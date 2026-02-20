"""Tests for workflow variables schema and validation."""

import pytest
from pydantic import ValidationError
from api.routes.workflow_variables import (
    VariableDefinition,
    VariableSchemaRequest,
    StepMappingEntry,
    VarType,
    _validate_type,
)


class TestVariableDefinition:
    def test_valid_string_var(self):
        v = VariableDefinition(name="my_var", type=VarType.STRING, description="test")
        assert v.name == "my_var"
        assert v.type == VarType.STRING
        assert v.required is False

    def test_valid_number_var(self):
        v = VariableDefinition(name="count", type=VarType.NUMBER, default_value=42, required=True)
        assert v.default_value == 42
        assert v.required is True

    def test_invalid_name_starts_with_digit(self):
        with pytest.raises(ValidationError):
            VariableDefinition(name="1invalid")

    def test_invalid_name_has_spaces(self):
        with pytest.raises(ValidationError):
            VariableDefinition(name="my var")

    def test_empty_name(self):
        with pytest.raises(ValidationError):
            VariableDefinition(name="")

    def test_all_types(self):
        for t in VarType:
            v = VariableDefinition(name=f"var_{t.value}", type=t)
            assert v.type == t

    def test_sensitive_flag(self):
        v = VariableDefinition(name="api_key", type=VarType.SECRET, sensitive=True)
        assert v.sensitive is True


class TestVariableSchemaRequest:
    def test_empty_list(self):
        req = VariableSchemaRequest(variables=[])
        assert len(req.variables) == 0

    def test_multiple_variables(self):
        req = VariableSchemaRequest(variables=[
            VariableDefinition(name="a"),
            VariableDefinition(name="b", type=VarType.NUMBER),
        ])
        assert len(req.variables) == 2


class TestStepMappingEntry:
    def test_valid_mapping(self):
        m = StepMappingEntry(
            step_id="step1",
            input_mapping={"url": "{{base_url}}/api"},
            output_mapping={"result": "api_response"},
        )
        assert m.step_id == "step1"
        assert m.input_mapping["url"] == "{{base_url}}/api"

    def test_empty_mappings(self):
        m = StepMappingEntry(step_id="step1")
        assert m.input_mapping == {}
        assert m.output_mapping == {}


class TestValidateType:
    def test_string_valid(self):
        assert _validate_type("hello", "string") is True

    def test_string_invalid(self):
        assert _validate_type(123, "string") is False

    def test_number_valid(self):
        assert _validate_type(42, "number") is True
        assert _validate_type(3.14, "number") is True

    def test_number_invalid(self):
        assert _validate_type("42", "number") is False

    def test_boolean_not_number(self):
        assert _validate_type(True, "number") is False

    def test_boolean_valid(self):
        assert _validate_type(True, "boolean") is True
        assert _validate_type(False, "boolean") is True

    def test_boolean_invalid(self):
        assert _validate_type(1, "boolean") is False

    def test_json_dict(self):
        assert _validate_type({"a": 1}, "json") is True

    def test_json_list(self):
        assert _validate_type([1, 2, 3], "json") is True

    def test_json_invalid(self):
        assert _validate_type("not json", "json") is False

    def test_list_valid(self):
        assert _validate_type([1, 2], "list") is True

    def test_list_invalid(self):
        assert _validate_type("not list", "list") is False

    def test_secret_valid(self):
        assert _validate_type("mysecret", "secret") is True

    def test_unknown_type(self):
        assert _validate_type("anything", "unknown") is True
