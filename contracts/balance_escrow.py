# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *


class BalanceEscrow(gl.Contract):
    owner: str
    fee_wallet: str
    judge_address: str
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

    settled_verdict_id: TreeMap[str, str]
    settled_fulfillment_pct: TreeMap[str, u256]
    settled_to_deliverer: TreeMap[str, u256]
    settled_to_payer: TreeMap[str, u256]
    settled_fee: TreeMap[str, u256]

    verdict_consumed: TreeMap[str, str]
    case_counter: u256

    def __init__(self, owner_address: str, fee_wallet_address: str, protocol_fee_bps: int):
        self.owner = owner_address
        self.fee_wallet = fee_wallet_address
        self.judge_address = ""
        self.protocol_fee_bps = u256(protocol_fee_bps)
        self.case_counter = u256(0)

    # ------------------------------------------------------------------ #
    # Admin
    # ------------------------------------------------------------------ #
    @gl.public.write
    def set_judge_address(self, judge_address: str, caller: str):
        if caller.lower() != self.owner.lower():
            raise Exception("Only owner can set judge")
        self.judge_address = judge_address

    @gl.public.write
    def set_protocol_fee_bps(self, bps: int, caller: str):
        if caller.lower() != self.owner.lower():
            raise Exception("Only owner can set fee")
        if bps < 0 or bps > 2000:
            raise Exception("Fee out of bounds")
        self.protocol_fee_bps = u256(bps)

    # ------------------------------------------------------------------ #
    # Token (mock genUSDC, open-mint testnet faucet)
    # ------------------------------------------------------------------ #
    @gl.public.write
    def mint(self, to_address: str, amount: int):
        to_address = to_address.lower()
        cur = self.balances[to_address] if to_address in self.balances else u256(0)
        self.balances[to_address] = u256(int(cur) + amount)

    # ------------------------------------------------------------------ #
    # Agreement lifecycle
    # ------------------------------------------------------------------ #
    @gl.public.write
    def create_agreement(
        self,
        spec: str,
        amount: int,
        deadline: str,
        deliverer_address: str,
        created_at: str,
        caller: str,
    ) -> str:
        caller = caller.lower()
        deliverer = deliverer_address.lower()
        if amount <= 0:
            raise Exception("Amount must be positive")
        if deliverer == caller:
            raise Exception("Payer and deliverer must differ")
        if spec is None or spec.strip() == "":
            raise Exception("Spec required")
        case_id = "case_" + str(int(self.case_counter))
        self.agreement_ids.append(case_id)
        self.agreement_payer[case_id] = caller
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
    def accept_agreement(self, case_id: str, caller: str):
        caller = caller.lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "created":
            raise Exception("Agreement not awaiting acceptance")
        if caller != self.agreement_deliverer[case_id].lower():
            raise Exception("Only the named deliverer can accept")
        self.agreement_status[case_id] = "accepted"

    @gl.public.write
    def fund_escrow(self, case_id: str, caller: str):
        caller = caller.lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "accepted":
            raise Exception("Agreement not accepted yet")
        if caller != self.agreement_payer[case_id].lower():
            raise Exception("Only the payer can fund")
        amount = int(self.agreement_amount[case_id])
        bal = int(self.balances[caller]) if caller in self.balances else 0
        if bal < amount:
            raise Exception("Insufficient genUSDC balance")
        self.balances[caller] = u256(bal - amount)
        self.agreement_status[case_id] = "active"

    @gl.public.write
    def submit_delivery(
        self,
        case_id: str,
        primary_url: str,
        secondary_url: str,
        statement: str,
        caller: str,
    ):
        caller = caller.lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "active":
            raise Exception("Agreement not active")
        if caller != self.agreement_deliverer[case_id].lower():
            raise Exception("Only the deliverer can submit delivery")
        self.del_primary_url[case_id] = primary_url
        self.del_secondary_url[case_id] = secondary_url
        self.del_statement[case_id] = statement
        self.del_submitted[case_id] = "true"
        self.agreement_status[case_id] = "delivered"

    @gl.public.write
    def accept_delivery(self, case_id: str, caller: str) -> str:
        caller = caller.lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "delivered":
            raise Exception("Nothing delivered to accept")
        if caller != self.agreement_payer[case_id].lower():
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
    def dispute_delivery(
        self,
        case_id: str,
        primary_url: str,
        secondary_url: str,
        statement: str,
        caller: str,
    ):
        caller = caller.lower()
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "delivered":
            raise Exception("Can only dispute a delivered agreement")
        if caller != self.agreement_payer[case_id].lower():
            raise Exception("Only the payer can dispute")
        self.pay_primary_url[case_id] = primary_url
        self.pay_secondary_url[case_id] = secondary_url
        self.pay_statement[case_id] = statement
        self.pay_submitted[case_id] = "true"
        self.agreement_status[case_id] = "disputed"

    # ------------------------------------------------------------------ #
    # Settlement — the only thing that moves escrowed money on a dispute.
    # Permissionless: it only ever executes the consensus verdict's split,
    # and only after verifying the verdict corresponds exactly to this
    # agreement, its locked spec, its parties, and the committed evidence.
    # ------------------------------------------------------------------ #
    @gl.public.write
    def settle_from_verdict(self, case_id: str, verdict_id: str) -> str:
        if self.judge_address == "":
            raise Exception("Judge not configured")
        if case_id not in self.agreement_status:
            raise Exception("Unknown agreement")
        if self.agreement_status[case_id] != "disputed":
            raise Exception("Agreement is not in dispute")
        if verdict_id in self.verdict_consumed and self.verdict_consumed[verdict_id] == "true":
            raise Exception("Verdict already settled")
        if self.del_submitted[case_id] != "true" or self.pay_submitted[case_id] != "true":
            raise Exception("Both parties must have submitted evidence")

        judge = gl.get_contract_at(Address(self.judge_address))
        v = judge.view().get_verdict(verdict_id)
        if not v or "case_id" not in v:
            raise Exception("Verdict not found")

        if str(v["case_id"]) != case_id:
            raise Exception("Verdict case_id mismatch")
        if str(v["spec_used"]).strip() != self.agreement_spec[case_id].strip():
            raise Exception("Verdict judged against a different spec")
        if str(v["payer_address"]).lower() != self.agreement_payer[case_id].lower():
            raise Exception("Verdict payer mismatch")
        if str(v["deliverer_address"]).lower() != self.agreement_deliverer[case_id].lower():
            raise Exception("Verdict deliverer mismatch")
        if str(v["deliverer_primary_url"]).strip() != self.del_primary_url[case_id].strip():
            raise Exception("Deliverer evidence mismatch (primary)")
        if str(v["deliverer_secondary_url"]).strip() != self.del_secondary_url[case_id].strip():
            raise Exception("Deliverer evidence mismatch (secondary)")
        if str(v["deliverer_statement"]).strip() != self.del_statement[case_id].strip():
            raise Exception("Deliverer evidence mismatch (statement)")
        if str(v["payer_primary_url"]).strip() != self.pay_primary_url[case_id].strip():
            raise Exception("Payer evidence mismatch (primary)")
        if str(v["payer_secondary_url"]).strip() != self.pay_secondary_url[case_id].strip():
            raise Exception("Payer evidence mismatch (secondary)")
        if str(v["payer_statement"]).strip() != self.pay_statement[case_id].strip():
            raise Exception("Payer evidence mismatch (statement)")

        pct = int(v["fulfillment_pct"])
        if pct < 0:
            pct = 0
        if pct > 100:
            pct = 100

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

        self.verdict_consumed[verdict_id] = "true"
        self.settled_verdict_id[case_id] = verdict_id
        self.settled_fulfillment_pct[case_id] = u256(pct)
        self.settled_to_deliverer[case_id] = u256(to_deliverer)
        self.settled_to_payer[case_id] = u256(to_payer)
        self.settled_fee[case_id] = u256(fee)
        self.agreement_status[case_id] = "settled"
        return "settled:" + str(pct) + ":" + str(to_deliverer) + ":" + str(to_payer)

    # ------------------------------------------------------------------ #
    # Views
    # ------------------------------------------------------------------ #
    @gl.public.view
    def balance_of(self, address: str) -> int:
        address = address.lower()
        return int(self.balances[address]) if address in self.balances else 0

    @gl.public.view
    def get_judge_address(self) -> str:
        return self.judge_address

    @gl.public.view
    def get_protocol_fee_bps(self) -> int:
        return int(self.protocol_fee_bps)

    @gl.public.view
    def is_verdict_consumed(self, verdict_id: str) -> str:
        return self.verdict_consumed[verdict_id] if verdict_id in self.verdict_consumed else "false"

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
