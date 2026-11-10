"""HTTP-only contract check for a running withdrawal-soles service.

This is the tool a teammate runs without the repository internals. It talks to
the public API with the agreed service JWT, creates one withdrawal, reverses it,
and verifies the wallet balance when the wallet URL is provided.

    .venv/bin/python scripts/wallet_contract_check.py \
        --base-url http://localhost:8080

    .venv/bin/python scripts/wallet_contract_check.py \
        --base-url http://<gateway> \
        --wallet-url http://52.67.162.209

The withdrawal is always reversed before exit. If a step fails after the debit,
the script tries the reversal and prints the `wallet_movement_id` to recover.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from withdrawal_soles.infrastructure.service_jwt import (  # noqa: E402
    sign_service_token,
)

DEFAULT_ACCOUNT_ID = "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11"
DEFAULT_USER_ID = "9d1e2f3a-4b5c-6d7e-8f90-1a2b3c4d5e6f"
SECRET = "dev-only-change-me"
ISSUER = "billetera-dev"


class Checker:
    """Collects pass/fail rows and prints them as they happen."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, passed: bool, detail: str) -> bool:
        self.rows.append((name, passed, detail))
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        return passed

    @property
    def failed(self) -> int:
        return sum(1 for _, passed, _ in self.rows if not passed)

    def summary(self) -> str:
        return f"{len(self.rows) - self.failed}/{len(self.rows)} checks passed"


def _token(subject: str) -> str:
    return sign_service_token(
        secret=SECRET,
        issuer=ISSUER,
        subject=subject,
        ttl_seconds=300,
    )


def _headers(
    token: str, user_id: str, key: str | None = None
) -> dict[str, str]:
    values = {
        "Authorization": f"Bearer {token}",
        "X-User-Id": user_id,
        "Content-Type": "application/json",
    }
    if key is not None:
        values["Idempotency-Key"] = key
    return values


def _detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:160]
    if isinstance(payload, dict):
        return str(payload.get("code") or payload.get("detail") or payload)
    return str(payload)[:160]


async def _wallet_balance(
    client: httpx.AsyncClient,
    wallet_url: str,
    id_usuario: int,
) -> int | None:
    try:
        response = await client.get(
            f"{wallet_url.rstrip('/')}/v1/wallets",
            params={"idUsuario": id_usuario},
            headers={"Authorization": f"Bearer {_token('retiros')}"},
        )
    except httpx.HTTPError:
        return None
    if response.status_code != 200:
        return None
    try:
        return int(response.json()["balance"])
    except (KeyError, TypeError, ValueError):
        return None


async def run(args: argparse.Namespace) -> int:
    checker = Checker()
    base_url = args.base_url.rstrip("/")
    wallet_url = args.wallet_url
    user_token = args.token or _token("retiros")
    key = f"contract-{uuid4()}"
    cents = int(Decimal(args.amount) * 100)

    created: dict[str, Any] | None = None
    reversed_ok = False

    async with httpx.AsyncClient(timeout=15.0) as client:
        health = await client.get(f"{base_url}/health")
        checker.check(
            "health",
            health.status_code == 200,
            f"HTTP {health.status_code}",
        )

        anonymous = await client.get(f"{base_url}/api/v1/withdrawals")
        checker.check(
            "token required",
            anonymous.status_code == 401
            and anonymous.json().get("code") == "UNAUTHORIZED",
            f"HTTP {anonymous.status_code} {_detail(anonymous)}",
        )

        no_identity = await client.get(
            f"{base_url}/api/v1/withdrawals",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        checker.check(
            "user identity required",
            no_identity.status_code == 401,
            f"HTTP {no_identity.status_code} {_detail(no_identity)}",
        )

        listing = await client.get(
            f"{base_url}/api/v1/withdrawals",
            headers=_headers(user_token, args.user_id),
        )
        checker.check(
            "authenticated list",
            listing.status_code == 200,
            f"HTTP {listing.status_code}",
        )

        balance_before = None
        if wallet_url:
            balance_before = await _wallet_balance(
                client, wallet_url, args.id_usuario
            )
            checker.check(
                "wallet balance readable",
                balance_before is not None,
                f"balance={balance_before} cents",
            )

        created_response = await client.post(
            f"{base_url}/api/v1/withdrawals",
            headers=_headers(user_token, args.user_id, key),
            json={
                "account_id": args.account_id,
                "amount": args.amount,
            },
        )
        body = created_response.json() if created_response.content else {}
        created = body if isinstance(body, dict) else None
        checker.check(
            "create withdrawal",
            created_response.status_code == 201
            and bool(body.get("wallet_movement_id"))
            and body.get("status") in {"COMPLETED", "APPROVED"},
            f"HTTP {created_response.status_code} status={body.get('status')} "
            f"wallet_movement_id={body.get('wallet_movement_id')}",
        )

        if created is None or not created.get("id"):
            return _finish(checker)

        replay = await client.post(
            f"{base_url}/api/v1/withdrawals",
            headers=_headers(user_token, args.user_id, key),
            json={
                "account_id": args.account_id,
                "amount": args.amount,
            },
        )
        replay_body = replay.json() if replay.content else {}
        checker.check(
            "idempotent replay",
            replay.status_code == 200
            and replay_body.get("id") == created.get("id"),
            f"HTTP {replay.status_code} same_id="
            f"{replay_body.get('id') == created.get('id')}",
        )

        if wallet_url and balance_before is not None:
            balance_after_debit = await _wallet_balance(
                client, wallet_url, args.id_usuario
            )
            checker.check(
                "balance after debit",
                balance_after_debit == balance_before - cents,
                f"{balance_before} -> {balance_after_debit} "
                f"(expected {balance_before - cents})",
            )

        reversal = await client.post(
            f"{base_url}/api/v1/withdrawals/{created['id']}/reverse",
            headers=_headers(user_token, args.user_id, f"{key}:reverse"),
            json={"reason": "contract check"},
        )
        reversal_body = reversal.json() if reversal.content else {}
        reversed_ok = (
            reversal.status_code == 200
            and reversal_body.get("status") == "REVERSED"
            and bool(reversal_body.get("wallet_reversal_movement_id"))
        )
        checker.check(
            "reverse withdrawal",
            reversed_ok,
            f"HTTP {reversal.status_code} "
            f"status={reversal_body.get('status')}",
        )

        second = await client.post(
            f"{base_url}/api/v1/withdrawals/{created['id']}/reverse",
            headers=_headers(user_token, args.user_id, f"{key}:reverse-2"),
            json={"reason": "contract check"},
        )
        checker.check(
            "second reverse rejected",
            second.status_code == 422
            and second.json().get("code") == "WALLET_ALREADY_REVERSED",
            f"HTTP {second.status_code} {_detail(second)}",
        )

        if wallet_url and balance_before is not None:
            balance_final = await _wallet_balance(
                client, wallet_url, args.id_usuario
            )
            checker.check(
                "balance restored",
                balance_final == balance_before,
                f"balance={balance_final} (expected {balance_before})",
            )

    if created and not reversed_ok:
        print(
            "\n[WARN] The withdrawal was debited but not reversed. "
            f"wallet_movement_id={created.get('wallet_movement_id')} "
            f"withdrawal_id={created.get('id')}",
            file=sys.stderr,
        )

    return _finish(checker)


def _finish(checker: Checker) -> int:
    print(f"\nSummary: {checker.summary()}")
    return 1 if checker.failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://localhost:8080",
        help="Running withdrawal-soles base URL.",
    )
    parser.add_argument(
        "--wallet-url",
        default=None,
        help="Optional wallet base URL to verify the balance.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Service JWT for withdrawal-soles. Defaults to the dev token.",
    )
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--account-id", default=DEFAULT_ACCOUNT_ID)
    parser.add_argument("--id-usuario", type=int, default=15)
    parser.add_argument(
        "--amount",
        default="10.00",
        help="Withdrawal amount in PEN. It is reversed at the end.",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
