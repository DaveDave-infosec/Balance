import pytest

CONTRACT = "contracts/balance.py"
SDK = "v0.2.16"


def _hex(addr):
    v = getattr(addr, "as_hex", None)
    return v if v else str(addr)


def test_addr_and_deploy(direct_deploy, direct_owner, direct_bob):
    print("\nOWNER repr:", repr(direct_owner), "| as_hex:", getattr(direct_owner, "as_hex", None), "| str:", str(direct_owner))
    print("BOB   repr:", repr(direct_bob), "| as_hex:", getattr(direct_bob, "as_hex", None), "| str:", str(direct_bob))
    c = direct_deploy(CONTRACT, 250, sdk_version=SDK)
    print("case_count:", c.get_case_count())
    print("owner:", c.get_owner())
    assert c.get_case_count() == 0


def test_create_and_read(direct_deploy, direct_vm, direct_owner, direct_bob):
    c = direct_deploy(CONTRACT, 250, sdk_version=SDK)
    direct_vm.sender = direct_owner
    bob_hex = _hex(direct_bob)
    print("\ndeliverer arg:", bob_hex)
    cid = c.create_agreement("test spec", 1000, "2026-08-01", bob_hex, "2026-07-05T00:00:00Z")
    print("create returned:", repr(cid))
    print("case_count:", c.get_case_count())
    ag = c.get_agreement("case_0")
    print("agreement:", ag)
    assert c.get_case_count() == 1
    assert ag["status"] == "created"
    assert ag["amount"] == 1000
