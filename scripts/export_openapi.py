"""Export the FastAPI contract to openapi.yaml.

Run from the repository root:

    .venv/bin/python scripts/export_openapi.py

The generated document is intentionally checked in so clients can consume the
contract without starting the service.
"""

from pathlib import Path

import yaml

from withdrawal_soles.main import app

OUTPUT = Path(__file__).resolve().parent.parent / "openapi.yaml"

OPERATION_METADATA = {
    ("/api/v1/withdrawals", "post"): (
        "createWithdrawal",
        "Create a PEN withdrawal",
        "Validate the account, enforce the per-operation and daily limits, "
        "debit the PEN wallet, persist the operation with its wallet ids, and "
        "report it to transaction-service.",
    ),
    ("/api/v1/withdrawals", "get"): (
        "listWithdrawals",
        "List owned withdrawals",
        "Return only operations owned by the caller, with optional filters and pagination.",
    ),
    ("/api/v1/withdrawals/{withdrawal_id}", "get"): (
        "getWithdrawal",
        "Read one owned withdrawal",
        "Return one operation when it belongs to the caller.",
    ),
    ("/api/v1/withdrawals/{withdrawal_id}/cancel", "post"): (
        "cancelWithdrawal",
        "Cancel a pending withdrawal",
        "Reject a PENDING operation. Repeating the request is idempotent.",
    ),
    ("/api/v1/withdrawals/{withdrawal_id}/report", "post"): (
        "retryWithdrawalReport",
        "Retry ledger reporting",
        "Retry reporting for an APPROVED operation. Returns 200 when the "
        "operation becomes COMPLETED and 202 when the ledger still fails.",
    ),
    ("/api/v1/withdrawals/{withdrawal_id}/reverse", "post"): (
        "reverseWithdrawal",
        "Reverse a debited withdrawal",
        "Reverse the full wallet debit for an APPROVED or COMPLETED operation "
        "and mark it REVERSED. A second reversal returns 422; an operation "
        "without a wallet debit returns 409.",
    ),
    ("/health", "get"): (
        "health",
        "Check database readiness",
        "Return 200 when the database is reachable and 503 otherwise.",
    ),
}


def enrich(spec: dict) -> dict:
    spec["info"]["title"] = "withdrawal-soles API"
    spec["info"]["description"] = (
        "PEN withdrawal microservice for the banking platform.\n\n"
        "Every request carries the gateway-injected `X-User-Id` header. Every "
        "mutating request also requires an `Idempotency-Key`. Amounts are "
        "decimal strings in PEN; the minimum is 10.00, the maximum per "
        "operation is 5000.00, and the daily accumulated limit per account is "
        "10000.00.\n\n"
        "The external PEN wallet is the balance owner. A successful withdrawal "
        "debits the wallet before it is persisted and stores the wallet and "
        "movement identifiers; `POST /api/v1/withdrawals/{id}/reverse` returns "
        "the full amount to the wallet."
    )
    spec["info"]["contact"] = {
        "name": "app-nube-2",
        "url": "https://github.com/J0sePs/app-nube-2",
    }
    spec["servers"] = [
        {
            "url": (
                "http://a6c1a4b5ffa8a44808f8a8a0784fe0d7-266125410"
                ".us-east-1.elb.amazonaws.com"
            ),
            "description": "AWS EKS public gateway (Traefik LoadBalancer)",
        },
        {
            "url": "http://localhost:8080",
            "description": "Local Docker Compose through Traefik",
        },
        {
            "url": "http://localhost:18080",
            "description": "EKS through kubectl port-forward",
        },
    ]
    spec["tags"] = [
        {
            "name": "withdrawals",
            "description": (
                "Create, list, read, cancel, reverse, and report PEN withdrawals."
            ),
        },
        {
            "name": "health",
            "description": "Database readiness for orchestration and the gateway.",
        },
    ]

    for path, methods in spec["paths"].items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            metadata = OPERATION_METADATA.get((path, method))
            if metadata:
                operation["operationId"], operation["summary"], operation["description"] = metadata

            for parameter in operation.get("parameters", []):
                if parameter["name"] == "X-User-Id":
                    parameter["required"] = True
                    parameter["description"] = (
                        "Caller identity injected by the API gateway. Must be a UUID."
                    )
                    parameter["schema"] = {"type": "string", "format": "uuid"}
                elif parameter["name"] == "Idempotency-Key":
                    parameter["description"] = (
                        "Client-generated key that makes the mutation safe to retry. "
                        "Reuse the same key for the same request; reusing it with a "
                        "different payload returns 409."
                    )
                    parameter["schema"] = {"type": "string", "minLength": 1}
                    if method in {"post", "put", "patch", "delete"}:
                        parameter["required"] = True

    withdrawal_create = spec["components"]["schemas"]["WithdrawalCreate"]
    amount = withdrawal_create["properties"]["amount"]
    amount["description"] = (
        "Amount in PEN as a decimal string with at most two decimal places. "
        "Minimum 10.00, maximum 5000.00 per operation."
    )
    amount["examples"] = ["250.00"]

    response = spec["components"]["schemas"]["WithdrawalResponse"]
    response["example"] = {
        "id": "14544b68-9c70-4365-bd40-6ba0824bba15",
        "account_id": "1c7a5e0e-4f4a-4a1f-9a3e-7b9f0d2a6c11",
        "amount": "250.00",
        "currency": "PEN",
        "status": "COMPLETED",
        "transaction_id": "aa3e255f-40b0-4054-80ee-0e637cb30060",
        "wallet_id": "a212968a-21d1-40f1-a47d-5f87c5b36a84",
        "wallet_movement_id": "5d0916cc-5cd9-4fdc-9671-79a79050e6e9",
        "wallet_reversal_movement_id": None,
        "created_at": "2026-10-30T17:56:55.809071Z",
        "updated_at": "2026-10-30T17:56:55.824911Z",
    }

    reverse = spec["components"]["schemas"].get("WithdrawalReverse")
    if reverse is not None:
        reverse["example"] = {
            "reason": "Reversal requested by the operations team",
        }

    return spec


def main() -> None:
    spec = enrich(app.openapi())
    OUTPUT.write_text(
        yaml.safe_dump(spec, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
