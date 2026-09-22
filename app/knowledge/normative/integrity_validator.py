"""Semantic integrity checks for Normative JSON 2.0."""

from .validation_codes import ValidationCode
from .validation_result import ValidationError


class IntegrityValidator:
    """Validate internal links, identifiers and provenance ranges."""

    def validate(self, document: dict) -> list[ValidationError]:
        errors: list[ValidationError] = []
        sections = document.get("structure", {}).get("sections", [])
        clauses = []
        for section in sections:
            clauses.extend(section.get("clauses", []))
        clause_ids = {clause.get("number") for clause in clauses if clause.get("number")}

        requirements = document.get("requirements", [])
        tables = document.get("tables", [])
        references = document.get("references", [])
        table_ids = {table.get("table_id") for table in tables if table.get("table_id")}
        reference_ids = {ref.get("reference_id") for ref in references if ref.get("reference_id")}

        errors.extend(self._duplicates(requirements, "requirement_id", ValidationCode.DUPLICATE_REQUIREMENT_ID, "requirements"))
        errors.extend(self._duplicates(tables, "table_id", ValidationCode.DUPLICATE_TABLE_ID, "tables"))
        errors.extend(self._duplicates(references, "reference_id", ValidationCode.DUPLICATE_REFERENCE_ID, "references"))

        page_count = document.get("document", {}).get("source", {}).get("pages")
        for index, requirement in enumerate(requirements):
            clause_id = requirement.get("clause_id")
            if clause_id not in clause_ids:
                errors.append(ValidationError(
                    ValidationCode.REQ_CLAUSE_NOT_FOUND,
                    f"$.requirements[{index}].clause_id",
                    f"Referenced clause does not exist: {clause_id}",
                    "integrity",
                ))
            for ref_index, table_id in enumerate(requirement.get("table_refs", [])):
                if table_id not in table_ids:
                    errors.append(ValidationError(
                        ValidationCode.TABLE_NOT_FOUND,
                        f"$.requirements[{index}].table_refs[{ref_index}]",
                        f"Referenced table does not exist: {table_id}",
                        "integrity",
                    ))
            errors.extend(self._validate_source(requirement.get("source"), f"$.requirements[{index}].source", page_count))

        for index, section in enumerate(sections):
            errors.extend(self._validate_range(section, f"$.structure.sections[{index}]"))
            for clause_index, clause in enumerate(section.get("clauses", [])):
                errors.extend(self._validate_range(clause, f"$.structure.sections[{index}].clauses[{clause_index}]"))
                errors.extend(self._validate_source(clause.get("source"), f"$.structure.sections[{index}].clauses[{clause_index}].source", page_count))

        return errors

    @staticmethod
    def _duplicates(items, key, code, root):
        seen = {}
        errors = []
        for index, item in enumerate(items):
            value = item.get(key)
            if value in seen:
                errors.append(ValidationError(code, f"$.{root}[{index}].{key}", f"Duplicate {key}: {value}", "integrity"))
            else:
                seen[value] = index
        return errors

    @staticmethod
    def _validate_range(item, path):
        start, end = item.get("page_start"), item.get("page_end")
        if start is not None and end is not None and start > end:
            return [ValidationError(ValidationCode.INVALID_PAGE_RANGE, path, "page_start must not exceed page_end", "integrity")]
        return []

    @staticmethod
    def _validate_source(source, path, page_count):
        if not source or page_count is None:
            return []
        errors = []
        for index, block in enumerate(source.get("blocks", [])):
            page = block.get("page")
            if page is not None and not 1 <= page <= page_count:
                errors.append(ValidationError(
                    ValidationCode.PAGE_OUT_OF_RANGE,
                    f"{path}.blocks[{index}].page",
                    f"Provenance page {page} is outside document range 1..{page_count}",
                    "integrity",
                ))
        return errors
