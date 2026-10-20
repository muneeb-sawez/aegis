"""AEGIS Contract Diff Engine (M4).

Compares old vs new API/schema JSON to detect breaking changes.
Docs: docs/04-ALGORITHMS.md §2.
Breaking change => C = 100.0
Safe / additive change => C = 0.0
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class DiffEntry(BaseModel):
    field: str
    change_type: str  # removed_field, type_change, added_required, added_optional, modified
    old_value: Any = None
    new_value: Any = None
    is_breaking: bool
    description: str


class ContractDiffResult(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    is_breaking: bool
    changes: list[DiffEntry] = Field(default_factory=list)


def diff_schemas(
    old_schema: dict[str, Any] | None,
    new_schema: dict[str, Any] | None,
) -> ContractDiffResult:
    """Compare two schemas (dictionaries of field_name -> type_or_spec).

    Rules:
    - Removed field: BREAKING
    - Changed field type: BREAKING
    - Added required field (or required=True): BREAKING
    - Added optional field: SAFE
    """
    if not old_schema and not new_schema:
        return ContractDiffResult(score=0.0, is_breaking=False, changes=[])
    if not old_schema and new_schema:
        # Pure addition of schema
        return ContractDiffResult(score=0.0, is_breaking=False, changes=[])
    if old_schema and not new_schema:
        # Complete removal of schema
        return ContractDiffResult(
            score=100.0,
            is_breaking=True,
            changes=[
                DiffEntry(
                    field="schema",
                    change_type="removed_entire_schema",
                    is_breaking=True,
                    description="Entire schema was removed",
                )
            ],
        )

    changes: list[DiffEntry] = []
    has_breaking = False

    old_props = old_schema.get("properties", old_schema)
    new_props = new_schema.get("properties", new_schema)

    # 1. Check for removed fields
    for field_name, old_spec in old_props.items():
        if field_name not in new_props:
            has_breaking = True
            changes.append(
                DiffEntry(
                    field=field_name,
                    change_type="removed_field",
                    old_value=old_spec,
                    new_value=None,
                    is_breaking=True,
                    description=f"Field '{field_name}' was removed from response schema",
                )
            )
        else:
            new_spec = new_props[field_name]
            old_type = old_spec.get("type") if isinstance(old_spec, dict) else str(old_spec)
            new_type = new_spec.get("type") if isinstance(new_spec, dict) else str(new_spec)
            if old_type != new_type:
                has_breaking = True
                changes.append(
                    DiffEntry(
                        field=field_name,
                        change_type="type_change",
                        old_value=old_type,
                        new_value=new_type,
                        is_breaking=True,
                        description=f"Field '{field_name}' changed type from '{old_type}' to '{new_type}'",
                    )
                )

    # 2. Check for newly added fields
    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))

    for field_name, new_spec in new_props.items():
        if field_name not in old_props:
            # If marked required, it breaks older clients
            if field_name in new_required or (isinstance(new_spec, dict) and new_spec.get("required") is True):
                has_breaking = True
                changes.append(
                    DiffEntry(
                        field=field_name,
                        change_type="added_required",
                        old_value=None,
                        new_value=new_spec,
                        is_breaking=True,
                        description=f"Field '{field_name}' was added as a mandatory required field",
                    )
                )
            else:
                changes.append(
                    DiffEntry(
                        field=field_name,
                        change_type="added_optional",
                        old_value=None,
                        new_value=new_spec,
                        is_breaking=False,
                        description=f"Field '{field_name}' added as an optional backwards-compatible field",
                    )
                )

    score = 100.0 if has_breaking else 0.0
    return ContractDiffResult(score=score, is_breaking=has_breaking, changes=changes)
