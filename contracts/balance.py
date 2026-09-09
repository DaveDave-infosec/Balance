# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import json
import hashlib


BALANCE_PROMPT = """You are Balance, an impartial settlement judge. Your job is to decide how much
of a digital deliverable was actually fulfilled, as a single percentage from 0
to 100, judged strictly against the acceptance criteria that BOTH parties locked
in before any work or dispute.

LOCKED ACCEPTANCE CRITERIA (the neutral yardstick — neither party can change this):
{spec}

DELIVERER'S SUBMITTED STATEMENT (a claim, NOT fact):
{deliverer_statement}

DELIVERER'S EVIDENCE (content fetched live from the URLs they submitted):
{deliverer_evidence}

PAYER'S SUBMITTED STATEMENT (a claim, NOT fact):
{payer_statement}

PAYER'S EVIDENCE (content fetched live from the URLs they submitted):
{payer_evidence}

How to judge:
1. VERIFY, DON'T TRUST. Never take either party's written statement as fact.
   Judge only against what the fetched evidence actually shows.
2. BROKEN OR EMPTY IS A SIGNAL. If a resource is NOT_PROVIDED,
   FETCH_FAILED_OR_UNREACHABLE, EMPTY_RESOURCE, or clearly unrelated to the
   spec, that counts AGAINST any claim depending on it.
3. INVESTIGATE DIVERGENCE. Where the two parties' evidence disagrees, rely on
   what the fetched content actually contains. The divergence itself is informative.
4. SCORE EACH CRITERION, THEN AGGREGATE. Break the locked criteria into checkable
   items, decide from the evidence whether each is fully, partially, or not met,
   and aggregate into one fulfillment_pct. Partial, good-faith work should land in
   the middle — not 0, not 100.
5. ONLY JUDGE WHAT IS CHECKABLE. If a criterion cannot be verified from
   web-fetchable evidence, say so and do not let it swing the score.

Respond ONLY as valid JSON, no markdown, no preamble:
{{
  "fulfillment_pct": 0-100,
  "confidence_level": "High" or "Moderate" or "Low" or "Contested",
  "deliverer_evidence_assessment": "1 sentence on what the deliverer's fetched resources actually showed",
  "payer_evidence_assessment": "1 sentence on what the payer's fetched resources actually showed",
  "divergence_note": "1 sentence on where the two bundles diverged and what you found",
  "reasoning_summary": "2-3 sentences explaining the fulfillment percentage, grounded in the fetched evidence",
  "minority_note": "1-2 sentences giving the strongest good-faith case that the percentage should be materially higher or lower — the dissenting view, preserved"
}}"""


class BalanceProtocol(gl.Contract):
    owner: str
    fee_wallet: str
    protocol_fee_bps: u256
    balances: TreeMap[str, u256]

    agreement_ids: DynArray[str]
    agreement_payer: TreeMap[str, str]
    agreement_deliverer: TreeMap[str, str]
    agreement_spec: TreeMap[str, str]
    agreement_amount: TreeMap[str, u256]
    agreement_deadline: TreeMap[str, str]
    agreement_status: TreeMap[str, str]
    agreement_created_at: TreeMap[str, str]

    del_primary_url: TreeMap[str, str]
    del_secondary_url: TreeMap[str, str]
    del_statement: TreeMap[str, str]
    del_submitted: TreeMap[str, str]

    pay_primary_url: TreeMap[str, str]
    pay_secondary_url: TreeMap[str, str]
    pay_statement: TreeMap[str, str]
    pay_submitted: TreeMap[str, str]

    confidence_level: TreeMap[str, str]
    reasoning_summary: TreeMap[str, str]
    minority_note: TreeMap[str, str]
    divergence_note: TreeMap[str, str]
    deliverer_evidence_assessment: TreeMap[str, str]
    payer_evidence_assessment: TreeMap[str, str]
    deliverer_evidence_hash: TreeMap[str, str]
    payer_evidence_hash: TreeMap[str, str]

    settled_fulfillment_pct: TreeMap[str, u256]
    settled_to_deliverer: TreeMap[str, u256]
    settled_to_payer: TreeMap[str, u256]
    settled_fee: TreeMap[str, u256]
    settled_verdict_id: TreeMap[str, str]

    case_counter: u256

    def __init__(self, protocol_fee_bps: int):
        deployer = str(gl.message.sender_address).lower()
        self.owner = deployer
        self.fee_wallet = deployer
        self.protocol_fee_bps = u256(protocol_fee_bps)
        self.case_counter = u256(0)

    @gl.public.write
    def set_protocol_fee_bps(self, bps: int):
        sender = str(gl.message.sender_address).lower()
        if sender != self.owner.lower():
            raise Exception("Only owner can set fee")
        if bps < 0 or bps > 2000:
            raise Exception("Fee out of bounds")
        self.protocol_fee_bps = u256(bps)

    # Controlled faucet: only the owner may mint the testnet settlement token.
    @gl.public.write
    def mint(self, to_address: str, amount: int):
        sender = str(gl.message.sender_address).lower()
        if sender != self.owner.lower():
            raise Exception("Only owner can mint")
        to_address = to_address.lower()
        cur = self.balances[to_address] if to_address in self.balances else u256(0)
        self.balances[to_address] = u256(int(cur) + amount)

    @gl.public.write
    def create_agreement(self, spec: str, amount: int, deadline: str, deliverer_address: str, created_at: str) -> str:
        payer = str(gl.message.sender_address).lower()
        deliverer = deliverer_address.lower()
        if amount <= 0:
            raise Exception("Amount must be positive")
        if deliverer == payer:
            raise Exception("Payer and deliverer must differ")
        if spec is None or spec.strip() == "":
            raise Exception("Spec required")
        case_id = "case_" + str(int(self.case_counter))
        self.agreement_ids.append(case_id)
        self.agreement_payer[case_id] = payer
        self.agreement_deliverer[case_id] = deliverer
        self.agreement_spec[case_id] = spec
        self.agreement_amount[case_id] = u256(amount)
        self.agreement_deadline[case_id] = deadline
        self.agreement_status[case_id] = "created"
        self.agreement_created_at[case_id] = created_at
        self.del_submitted[case_id] = "false"
        self.pay_submitted[case_id] = "false"
        self.case_counter = u256(int(self.case_counter) + 1)
        return case_id

    @gl.public.write
    def accept_agreement(self, case_id: str):
        sender = str(gl.message.sender_address).lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "created":
            raise Exception("Agreement not awaiting acceptance")
        if sender != self.agreement_deliverer[case_id].lower():
            raise Exception("Only the named deliverer can accept")
        self.agreement_status[case_id] = "accepted"

    @gl.public.write
    def fund_escrow(self, case_id: str):
        sender = str(gl.message.sender_address).lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "accepted":
            raise Exception("Agreement not accepted yet")
        if sender != self.agreement_payer[case_id].lower():
            raise Exception("Only the payer can fund")
        amount = int(self.agreement_amount[case_id])
        bal = int(self.balances[sender]) if sender in self.balances else 0
        if bal < amount:
            raise Exception("Insufficient genUSDC balance")
        self.balances[sender] = u256(bal - amount)
        self.agreement_status[case_id] = "active"

    @gl.public.write
    def submit_delivery(self, case_id: str, primary_url: str, secondary_url: str, statement: str):
        sender = str(gl.message.sender_address).lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "active":
            raise Exception("Agreement not active")
        if sender != self.agreement_deliverer[case_id].lower():
            raise Exception("Only the deliverer can submit delivery")
        self.del_primary_url[case_id] = primary_url
        self.del_secondary_url[case_id] = secondary_url
        self.del_statement[case_id] = statement
        self.del_submitted[case_id] = "true"
        self.agreement_status[case_id] = "delivered"

    @gl.public.write
    def accept_delivery(self, case_id: str) -> str:
        sender = str(gl.message.sender_address).lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "delivered":
            raise Exception("Nothing delivered to accept")
        if sender != self.agreement_payer[case_id].lower():
            raise Exception("Only the payer can accept delivery")
        amount = int(self.agreement_amount[case_id])
        fee = (amount * int(self.protocol_fee_bps)) // 10000
        to_deliverer = amount - fee
        deliverer = self.agreement_deliverer[case_id].lower()
        fee_wallet = self.fee_wallet.lower()
        dbal = int(self.balances[deliverer]) if deliverer in self.balances else 0
        self.balances[deliverer] = u256(dbal + to_deliverer)
        fbal = int(self.balances[fee_wallet]) if fee_wallet in self.balances else 0
        self.balances[fee_wallet] = u256(fbal + fee)
        self.settled_verdict_id[case_id] = "accepted_in_full"
        self.settled_fulfillment_pct[case_id] = u256(100)
        self.settled_to_deliverer[case_id] = u256(to_deliverer)
        self.settled_to_payer[case_id] = u256(0)
        self.settled_fee[case_id] = u256(fee)
        self.agreement_status[case_id] = "settled"
        return "released:" + str(to_deliverer)

    @gl.public.write
    def dispute_delivery(self, case_id: str, primary_url: str, secondary_url: str, statement: str) -> str:
        sender = str(gl.message.sender_address).lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "delivered":
            raise Exception("Can only dispute a delivered agreement")
        if sender != self.agreement_payer[case_id].lower():
            raise Exception("Only the payer can dispute")

        self.pay_primary_url[case_id] = primary_url
        self.pay_secondary_url[case_id] = secondary_url
        self.pay_statement[case_id] = statement
        self.pay_submitted[case_id] = "true"

        spec_local = self.agreement_spec[case_id]
        del_primary = self.del_primary_url[case_id]
        del_secondary = self.del_secondary_url[case_id]
        del_statement = self.del_statement[case_id]
        pay_primary = primary_url
        pay_secondary = secondary_url
        pay_stmt = statement

        def _fetch_one(url: str):
            if not url or not url.strip():
                return ("NOT_PROVIDED", "")
            try:
                content = gl.nondet.web.render(url, mode="text")
                if content is None:
                    return ("FETCH_FAILED_OR_UNREACHABLE", "")
                text = str(content).strip()
                if text == "":
                    return ("EMPTY_RESOURCE", "")
                return ("OK", text)
            except Exception:
                return ("FETCH_FAILED_OR_UNREACHABLE", "")

        def _bundle(primary_url: str, secondary_url: str) -> str:
            p_status, p_text = _fetch_one(primary_url)
            s_status, s_text = _fetch_one(secondary_url)
            full = json.dumps({
                "primary": {"url": primary_url, "status": p_status, "content": p_text},
                "secondary": {"url": secondary_url, "status": s_status, "content": s_text},
            }, sort_keys=True)
            h = hashlib.sha256(full.encode("utf-8")).hexdigest()
            view = json.dumps({
                "primary": {"url": primary_url, "status": p_status, "content": p_text[:8000]},
                "secondary": {"url": secondary_url, "status": s_status, "content": s_text[:8000]},
            }, sort_keys=True)
            return json.dumps({"hash": h, "bytes": len(full), "view": view}, sort_keys=True)

        def fetch_deliverer() -> str:
            return _bundle(del_primary, del_secondary)
        deliverer_bundle = gl.eq_principle.strict_eq(fetch_deliverer)

        def fetch_payer() -> str:
            return _bundle(pay_primary, pay_secondary)
        payer_bundle = gl.eq_principle.strict_eq(fetch_payer)

        del_parsed = json.loads(deliverer_bundle)
        pay_parsed = json.loads(payer_bundle)
        del_evidence_local = del_parsed["view"]
        pay_evidence_local = pay_parsed["view"]
        del_hash_local = del_parsed["hash"]
        pay_hash_local = pay_parsed["hash"]

        def judge_fn() -> str:
            prompt = BALANCE_PROMPT.format(
                spec=spec_local,
                deliverer_statement=del_statement,
                deliverer_evidence=del_evidence_local,
                payer_statement=pay_stmt,
                payer_evidence=pay_evidence_local,
            )
            result = gl.nondet.exec_prompt(prompt, response_format="json")
            if isinstance(result, str):
                parsed = json.loads(result)
            else:
                parsed = result
            return json.dumps(parsed, sort_keys=True)
        principle = (
            "The verdict must agree on fulfillment_pct within a tolerance of 10 "
            "points. It must agree on the coarse outcome band: not fulfilled "
            "(0-33), partially fulfilled (34-66), or substantially fulfilled "
            "(67-100). The reasoning must be grounded in the fetched evidence and "
            "the locked acceptance criteria, never in either party's self-description."
        )
        judgment_str = gl.eq_principle.prompt_comparative(judge_fn, principle)
        judgment = json.loads(judgment_str)

        pct_raw = judgment.get("fulfillment_pct", 0)
        try:
            pct = int(pct_raw)
        except (TypeError, ValueError):
            pct = 0
        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100

        self.confidence_level[case_id] = str(judgment.get("confidence_level", "Low"))
        self.reasoning_summary[case_id] = str(judgment.get("reasoning_summary", ""))
        self.minority_note[case_id] = str(judgment.get("minority_note", ""))
        self.divergence_note[case_id] = str(judgment.get("divergence_note", ""))
        self.deliverer_evidence_assessment[case_id] = str(judgment.get("deliverer_evidence_assessment", ""))
        self.payer_evidence_assessment[case_id] = str(judgment.get("payer_evidence_assessment", ""))
        self.deliverer_evidence_hash[case_id] = del_hash_local
        self.payer_evidence_hash[case_id] = pay_hash_local

        amount = int(self.agreement_amount[case_id])
        fee = (amount * int(self.protocol_fee_bps)) // 10000
        distributable = amount - fee
        to_deliverer = (distributable * pct) // 100
        to_payer = distributable - to_deliverer

        deliverer = self.agreement_deliverer[case_id].lower()
        payer = self.agreement_payer[case_id].lower()
        fee_wallet = self.fee_wallet.lower()

        dbal = int(self.balances[deliverer]) if deliverer in self.balances else 0
        self.balances[deliverer] = u256(dbal + to_deliverer)
        pbal = int(self.balances[payer]) if payer in self.balances else 0
        self.balances[payer] = u256(pbal + to_payer)
        fbal = int(self.balances[fee_wallet]) if fee_wallet in self.balances else 0
        self.balances[fee_wallet] = u256(fbal + fee)

        self.settled_fulfillment_pct[case_id] = u256(pct)
        self.settled_to_deliverer[case_id] = u256(to_deliverer)
        self.settled_to_payer[case_id] = u256(to_payer)
        self.settled_fee[case_id] = u256(fee)
        self.settled_verdict_id[case_id] = "consensus"
        self.agreement_status[case_id] = "settled"
        return "settled:" + str(pct) + ":" + str(to_deliverer) + ":" + str(to_payer)

    @gl.public.view
    def balance_of(self, address: str) -> int:
        address = address.lower()
        return int(self.balances[address]) if address in self.balances else 0

    @gl.public.view
    def get_protocol_fee_bps(self) -> int:
        return int(self.protocol_fee_bps)

    @gl.public.view
    def get_owner(self) -> str:
        return self.owner

    def _build_agreement(self, case_id: str) -> dict:
        return {
            "case_id": case_id,
            "payer": self.agreement_payer[case_id],
            "deliverer": self.agreement_deliverer[case_id],
            "spec": self.agreement_spec[case_id],
            "amount": int(self.agreement_amount[case_id]),
            "deadline": self.agreement_deadline[case_id],
            "status": self.agreement_status[case_id],
            "created_at": self.agreement_created_at[case_id],
            "deliverer_submitted": self.del_submitted[case_id] if case_id in self.del_submitted else "false",
            "deliverer_primary_url": self.del_primary_url[case_id] if case_id in self.del_primary_url else "",
            "deliverer_secondary_url": self.del_secondary_url[case_id] if case_id in self.del_secondary_url else "",
            "deliverer_statement": self.del_statement[case_id] if case_id in self.del_statement else "",
            "payer_submitted": self.pay_submitted[case_id] if case_id in self.pay_submitted else "false",
            "payer_primary_url": self.pay_primary_url[case_id] if case_id in self.pay_primary_url else "",
            "payer_secondary_url": self.pay_secondary_url[case_id] if case_id in self.pay_secondary_url else "",
            "payer_statement": self.pay_statement[case_id] if case_id in self.pay_statement else "",
            "confidence_level": self.confidence_level[case_id] if case_id in self.confidence_level else "",
            "reasoning_summary": self.reasoning_summary[case_id] if case_id in self.reasoning_summary else "",
            "minority_note": self.minority_note[case_id] if case_id in self.minority_note else "",
            "divergence_note": self.divergence_note[case_id] if case_id in self.divergence_note else "",
            "deliverer_evidence_assessment": self.deliverer_evidence_assessment[case_id] if case_id in self.deliverer_evidence_assessment else "",
            "payer_evidence_assessment": self.payer_evidence_assessment[case_id] if case_id in self.payer_evidence_assessment else "",
            "deliverer_evidence_hash": self.deliverer_evidence_hash[case_id] if case_id in self.deliverer_evidence_hash else "",
            "payer_evidence_hash": self.payer_evidence_hash[case_id] if case_id in self.payer_evidence_hash else "",
            "settled_verdict_id": self.settled_verdict_id[case_id] if case_id in self.settled_verdict_id else "",
            "settled_fulfillment_pct": int(self.settled_fulfillment_pct[case_id]) if case_id in self.settled_fulfillment_pct else 0,
            "settled_to_deliverer": int(self.settled_to_deliverer[case_id]) if case_id in self.settled_to_deliverer else 0,
            "settled_to_payer": int(self.settled_to_payer[case_id]) if case_id in self.settled_to_payer else 0,
            "settled_fee": int(self.settled_fee[case_id]) if case_id in self.settled_fee else 0,
        }

    @gl.public.view
    def get_agreement(self, case_id: str) -> dict:
        if case_id not in self.agreement_status:
            return {}
        return self._build_agreement(case_id)

    @gl.public.view
    def get_all_agreements(self) -> list:
        out = []
        for i in range(len(self.agreement_ids) - 1, -1, -1):
            out.append(self._build_agreement(self.agreement_ids[i]))
        return out

    @gl.public.view
    def get_agreements_by_party(self, address: str) -> list:
        address = address.lower()
        out = []
        for i in range(len(self.agreement_ids) - 1, -1, -1):
            cid = self.agreement_ids[i]
            if self.agreement_payer[cid].lower() == address or self.agreement_deliverer[cid].lower() == address:
                out.append(self._build_agreement(cid))
        return out

    @gl.public.view
    def get_case_count(self) -> u256:
        return u256(len(self.agreement_ids))
