import pytest

CONTRACT = "contracts/balance.py"
SDK = "v0.2.16"


def _hex(addr) -> str:
    # direct_* fixtures are raw 20-byte bytes; the contract wants lowercase hex
    return "0x" + addr.hex()


def _deploy(direct_deploy):
    return direct_deploy(CONTRACT, 250, sdk_version=SDK)


def _to_active(c, vm, owner, deliverer, amount=1000):
    vm.sender = owner
    c.mint(_hex(owner), amount)
    c.create_agreement("spec: deliver the thing", amount, "2026-08-01", _hex(deliverer), "2026-07-05T00:00:00Z")
    vm.sender = deliverer
    c.accept_agreement("case_0")
    vm.sender = owner
    c.fund_escrow("case_0")


def _to_delivered(c, vm, owner, deliverer, amount=1000):
    _to_active(c, vm, owner, deliverer, amount)
    vm.sender = deliverer
    c.submit_delivery("case_0", "https://example.com", "", "delivered")


def test_owner_is_deployer(direct_deploy, direct_owner):
    c = _deploy(direct_deploy)
    assert c.get_owner() == _hex(direct_owner)


def test_only_owner_can_mint(direct_deploy, direct_vm, direct_owner, direct_alice):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only owner can mint"):
        c.mint(_hex(direct_alice), 1000)
    direct_vm.sender = direct_owner
    c.mint(_hex(direct_alice), 1000)
    assert c.balance_of(_hex(direct_alice)) == 1000


def test_create_requires_distinct_parties(direct_deploy, direct_vm, direct_owner):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("Payer and deliverer must differ"):
        c.create_agreement("spec", 1000, "2026-08-01", _hex(direct_owner), "t")


def test_create_records_sender_as_payer(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_owner
    c.create_agreement("spec", 1000, "2026-08-01", _hex(direct_bob), "t")
    ag = c.get_agreement("case_0")
    assert ag["payer"] == _hex(direct_owner)
    assert ag["deliverer"] == _hex(direct_bob)
    assert ag["status"] == "created"


def test_only_deliverer_can_accept(direct_deploy, direct_vm, direct_owner, direct_bob, direct_alice):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_owner
    c.create_agreement("spec", 1000, "2026-08-01", _hex(direct_bob), "t")
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the named deliverer can accept"):
        c.accept_agreement("case_0")
    direct_vm.sender = direct_bob
    c.accept_agreement("case_0")
    assert c.get_agreement("case_0")["status"] == "accepted"


def test_only_payer_can_fund(direct_deploy, direct_vm, direct_owner, direct_bob, direct_alice):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_owner
    c.create_agreement("spec", 1000, "2026-08-01", _hex(direct_bob), "t")
    direct_vm.sender = direct_bob
    c.accept_agreement("case_0")
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the payer can fund"):
        c.fund_escrow("case_0")


def test_fund_requires_balance_then_activates(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_owner
    c.create_agreement("spec", 1000, "2026-08-01", _hex(direct_bob), "t")
    direct_vm.sender = direct_bob
    c.accept_agreement("case_0")
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("Insufficient genUSDC balance"):
        c.fund_escrow("case_0")
    c.mint(_hex(direct_owner), 1000)
    c.fund_escrow("case_0")
    assert c.get_agreement("case_0")["status"] == "active"
    assert c.balance_of(_hex(direct_owner)) == 0


def test_cannot_fund_before_accept(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_owner
    c.mint(_hex(direct_owner), 1000)
    c.create_agreement("spec", 1000, "2026-08-01", _hex(direct_bob), "t")
    with direct_vm.expect_revert("Agreement not accepted yet"):
        c.fund_escrow("case_0")


def test_cannot_deliver_before_active(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_owner
    c.create_agreement("spec", 1000, "2026-08-01", _hex(direct_bob), "t")
    direct_vm.sender = direct_bob
    c.accept_agreement("case_0")
    with direct_vm.expect_revert("Agreement not active"):
        c.submit_delivery("case_0", "https://x.com", "", "s")


def test_cannot_dispute_before_delivered(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _to_active(c, direct_vm, direct_owner, direct_bob)
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("Can only dispute a delivered agreement"):
        c.dispute_delivery("case_0", "https://x.com", "", "s")


def test_only_deliverer_can_submit(direct_deploy, direct_vm, direct_owner, direct_bob, direct_alice):
    c = _deploy(direct_deploy)
    _to_active(c, direct_vm, direct_owner, direct_bob)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the deliverer can submit delivery"):
        c.submit_delivery("case_0", "https://x.com", "", "s")
    direct_vm.sender = direct_bob
    c.submit_delivery("case_0", "https://x.com", "", "s")
    assert c.get_agreement("case_0")["status"] == "delivered"


def test_accept_in_full_pays_and_settles(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _to_delivered(c, direct_vm, direct_owner, direct_bob, amount=1000)
    direct_vm.sender = direct_owner
    c.accept_delivery("case_0")
    ag = c.get_agreement("case_0")
    assert ag["status"] == "settled"
    assert ag["settled_fulfillment_pct"] == 100
    assert ag["settled_fee"] == 25
    assert ag["settled_to_deliverer"] == 975
    assert ag["settled_to_payer"] == 0
    assert c.balance_of(_hex(direct_bob)) == 975


def test_only_payer_can_accept_delivery(direct_deploy, direct_vm, direct_owner, direct_bob, direct_alice):
    c = _deploy(direct_deploy)
    _to_delivered(c, direct_vm, direct_owner, direct_bob)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("Only the payer can accept delivery"):
        c.accept_delivery("case_0")


def test_dispute_settles_by_consensus_pct(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _to_delivered(c, direct_vm, direct_owner, direct_bob, amount=1000)

    direct_vm.mock_web(r".*", {"method": "GET", "status": 200, "body": "evidence: the deliverable exists"})
    verdict = (
        '{"fulfillment_pct": 60, "confidence_level": "High", '
        '"deliverer_evidence_assessment": "repo present", '
        '"payer_evidence_assessment": "matches", '
        '"divergence_note": "none", '
        '"reasoning_summary": "3 of 5 criteria met", '
        '"minority_note": "could argue higher"}'
    )
    direct_vm.mock_llm(r".*", verdict)

    direct_vm.sender = direct_owner  # the payer disputes
    c.dispute_delivery("case_0", "https://example.com", "", "loads but incomplete")

    ag = c.get_agreement("case_0")
    assert ag["status"] == "settled"
    assert ag["settled_fulfillment_pct"] == 60
    # 1000 - 2.5% fee = 975 distributable; 60% -> 585 deliverer, 390 refund
    assert ag["settled_fee"] == 25
    assert ag["settled_to_deliverer"] == 585
    assert ag["settled_to_payer"] == 390
    assert c.balance_of(_hex(direct_bob)) == 585
    assert c.balance_of(_hex(direct_owner)) == 415  # 390 refund + 25 fee (owner is fee_wallet)
    # evidence hashes recorded (immutable binding, sha256 hexdigest = 64 chars)
    assert len(ag["deliverer_evidence_hash"]) == 64
    assert len(ag["payer_evidence_hash"]) == 64
    assert ag["reasoning_summary"] == "3 of 5 criteria met"
    assert ag["minority_note"] == "could argue higher"


def test_dispute_low_verdict_refunds_payer(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _to_delivered(c, direct_vm, direct_owner, direct_bob, amount=1000)

    direct_vm.mock_web(r".*", {"method": "GET", "status": 200, "body": "404 not found"})
    verdict = (
        '{"fulfillment_pct": 10, "confidence_level": "High", '
        '"deliverer_evidence_assessment": "broken", '
        '"payer_evidence_assessment": "confirms broken", '
        '"divergence_note": "none", '
        '"reasoning_summary": "almost nothing delivered", '
        '"minority_note": "n/a"}'
    )
    direct_vm.mock_llm(r".*", verdict)

    direct_vm.sender = direct_owner
    c.dispute_delivery("case_0", "https://example.com", "", "does not resolve")

    ag = c.get_agreement("case_0")
    assert ag["status"] == "settled"
    assert ag["settled_fulfillment_pct"] == 10
    # 975 distributable; 10% -> 97 deliverer, 878 refund
    assert ag["settled_to_deliverer"] == 97
    assert ag["settled_to_payer"] == 878
    assert c.balance_of(_hex(direct_bob)) == 97


# ---------------- V2.1: fee-lock, deadlines, malformed recovery ----------------

def _warp(vm, ts):
    vm.warp(ts)
    import sys
    gl = sys.modules.get("genlayer.gl")
    if gl is not None and getattr(gl, "message_raw", None) is not None:
        gl.message_raw["datetime"] = ts


def _funded(c, vm, owner, deliverer, deadline, amount=1000):
    vm.sender = owner
    c.mint(_hex(owner), amount)
    c.create_agreement("spec: deliver X", amount, deadline, _hex(deliverer), "2026-07-05")
    vm.sender = deliverer
    c.accept_agreement("case_0")
    vm.sender = owner
    c.fund_escrow("case_0")


def _delivered(c, vm, owner, deliverer, deadline, amount=1000):
    _funded(c, vm, owner, deliverer, deadline, amount)
    vm.sender = deliverer
    c.submit_delivery("case_0", "https://example.com", "", "delivered")


VALID_VERDICT = '{"fulfillment_pct": 70, "confidence_level": "High", "reasoning_summary": "ok", "minority_note": "n/a", "divergence_note": "none", "deliverer_evidence_assessment": "a", "payer_evidence_assessment": "b"}'


def test_fee_locked_at_creation(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _delivered(c, direct_vm, direct_owner, direct_bob, "2026-08-01", amount=1000)
    direct_vm.sender = direct_owner
    c.set_protocol_fee_bps(1000)  # owner raises global fee to 10% AFTER creation
    c.accept_delivery("case_0")
    ag = c.get_agreement("case_0")
    assert ag["settled_fee"] == 25          # locked 2.5%, not the new 10%
    assert ag["settled_to_deliverer"] == 975


def test_malformed_verdict_reverts_then_recovers(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _delivered(c, direct_vm, direct_owner, direct_bob, "2026-08-01")
    direct_vm.mock_web(r".*", {"method": "GET", "status": 200, "body": "evidence"})
    direct_vm.mock_llm(r".*", '{"oops": true}')  # missing fulfillment_pct
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("Malformed verdict"):
        c.dispute_delivery("case_0", "https://example.com", "", "review")
    assert c.get_agreement("case_0")["status"] == "delivered"   # not stranded
    assert c.balance_of(_hex(direct_bob)) == 0                  # not paid
    direct_vm.clear_mocks()
    direct_vm.mock_web(r".*", {"method": "GET", "status": 200, "body": "evidence"})
    direct_vm.mock_llm(r".*", VALID_VERDICT)
    c.dispute_delivery("case_0", "https://example.com", "", "review")
    ag = c.get_agreement("case_0")
    assert ag["status"] == "settled"
    assert ag["settled_fulfillment_pct"] == 70


def test_unavailable_url_still_settles(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _delivered(c, direct_vm, direct_owner, direct_bob, "2026-08-01")
    # no web mock => fetch fails (FETCH_FAILED), but consensus still returns a verdict
    direct_vm.mock_llm(r".*", '{"fulfillment_pct": 5, "confidence_level": "Low", "reasoning_summary": "nothing fetched", "minority_note": "n/a", "divergence_note": "none", "deliverer_evidence_assessment": "broken", "payer_evidence_assessment": "broken"}')
    direct_vm.sender = direct_owner
    c.dispute_delivery("case_0", "https://example.com", "", "does not resolve")
    ag = c.get_agreement("case_0")
    assert ag["status"] == "settled"
    assert ag["settled_fulfillment_pct"] == 5


def test_reclaim_expired_refunds_payer(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _funded(c, direct_vm, direct_owner, direct_bob, "2026-08-01", amount=1000)
    _warp(direct_vm, "2027-01-01T00:00:00Z")
    direct_vm.sender = direct_owner
    c.reclaim_expired("case_0")
    ag = c.get_agreement("case_0")
    assert ag["status"] == "refunded"
    assert ag["settled_to_payer"] == 1000
    assert c.balance_of(_hex(direct_owner)) == 1000


def test_reclaim_before_deadline_reverts(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _funded(c, direct_vm, direct_owner, direct_bob, "2099-01-01", amount=1000)
    _warp(direct_vm, "2026-01-01T00:00:00Z")
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("deadline has not passed"):
        c.reclaim_expired("case_0")


def test_claim_stale_delivery(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _delivered(c, direct_vm, direct_owner, direct_bob, "2026-08-01")
    _warp(direct_vm, "2027-01-01T00:00:00Z")
    direct_vm.sender = direct_bob
    c.claim_stale_delivery("case_0")
    ag = c.get_agreement("case_0")
    assert ag["status"] == "settled"
    assert ag["settled_to_deliverer"] == 975
    assert c.balance_of(_hex(direct_bob)) == 975


def test_cancel_before_funding(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    direct_vm.sender = direct_owner
    c.create_agreement("spec", 1000, "2026-08-01", _hex(direct_bob), "2026-07-05")
    c.cancel_agreement("case_0")
    assert c.get_agreement("case_0")["status"] == "cancelled"


def test_cannot_cancel_after_funding(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = _deploy(direct_deploy)
    _funded(c, direct_vm, direct_owner, direct_bob, "2026-08-01")
    direct_vm.sender = direct_owner
    with direct_vm.expect_revert("Can only cancel before the escrow is funded"):
        c.cancel_agreement("case_0")
