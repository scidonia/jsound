# jSound - JSON Schema Subsumption Checker

jSound is a tool that checks **JSON Schema subsumption** using Z3 SMT solver. It determines whether one JSON schema is compatible with another by checking if the producer schema is a subset of the consumer schema.

## 🎯 What is Schema Subsumption?

Given two JSON schemas P (producer) and C (consumer), we say **P ⊆ C** (P subsumes C) if every JSON document that validates against P also validates against C. 

jSound checks this by solving: **P ∧ ¬C is UNSAT**
- If **UNSAT**: Schemas are compatible (P ⊆ C)
- If **SAT**: Schemas are incompatible, and jSound provides a counterexample

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Z3 SMT solver library (see installation options below)

### Installation Options

#### Option 1: Install from PyPI (Recommended)

```bash
# Install directly from PyPI
pip install jsound

# Or using pipx for isolated installation
pipx install jsound
```

#### Option 2: Install from Source

```bash
git clone <repository-url>
cd jsound
pip install .
```

#### Option 3: Development Setup with Nix/uv

```bash
git clone <repository-url>
cd jsound
direnv allow  # Sets up Nix environment with Z3
```

### Z3 Solver Installation

jSound requires the Z3 SMT solver library. Install it using your system package manager:

**Ubuntu/Debian:**
```bash
sudo apt-get install libz3-dev z3
```

**macOS (Homebrew):**
```bash
brew install z3
```

**Windows:**
- Download from [Z3 releases](https://github.com/Z3Prover/z3/releases)
- Or use conda: `conda install -c conda-forge z3`

**Python z3-solver package:**
```bash
pip install z3-solver
```

### Usage

```bash
# After pip/pipx installation
jsound producer_schema.json consumer_schema.json

# Or with uv (development)
uv run jsound producer_schema.json consumer_schema.json
```

## 📖 Usage Examples

### Basic Usage

```bash
# Check if producer schema is compatible with consumer schema
jsound examples/producer.json examples/consumer.json

# With uv (development)
uv run jsound examples/producer.json examples/consumer.json
```

**Compatible case:**
```json
// producer.json - More restrictive
{"type": "string", "minLength": 5}

// consumer.json - Less restrictive
{"type": "string"}
```
Output: `✓ Schemas are compatible`

**Incompatible case:**
```json
// producer.json - Allows strings OR numbers
{"type": ["string", "number"]}

// consumer.json - Only allows strings
{"type": "string"}
```
Output: `✗ Schemas are incompatible` (with counterexample)

### Command Line Options

```bash
jsound [OPTIONS] PRODUCER_SCHEMA_FILE CONSUMER_SCHEMA_FILE

Options:
  --max-array-length INTEGER     Maximum array length for bounds [default: 50]
  --max-recursion-depth INTEGER  Maximum $ref unrolling depth [default: 3]
  --timeout INTEGER              Z3 solver timeout in seconds [default: 30]
  --output-format TEXT           Output format: json, pretty, or minimal [default: pretty]
  --counterexample-file PATH     Save counterexample to file
  --verbose                      Enable verbose output
  --explanations                 Enable enhanced explanations for incompatibilities
```

### Output Formats

**Pretty format (default):**
```
✓ Schemas are compatible
Producer schema ⊆ Consumer schema

Solver time: 0.012s
```

**JSON format:**
```json
{
  "compatible": true,
  "counterexample": null,
  "solver_time": 0.012
}
```

**Minimal format:**
```
compatible
```

### Exit Codes

- `0`: Schemas are compatible
- `1`: Schemas are incompatible
- `2`: Error (invalid schema, timeout, etc.)

### Enhanced Explanations

jSound provides detailed explanations for schema incompatibilities with the `--explanations` flag:

```bash
jsound --explanations producer.json consumer.json
```

**Example enhanced output:**
```
✗ Schemas are incompatible

Counterexample: {"priority": "critical", "status": "active"}

Explanation: Property 'priority' enum mismatch: producer allows ['critical', 'urgent'] not in consumer enum ['low', 'medium', 'high'] | Property 'status' const mismatch: producer requires 'active', consumer requires 'enabled'

Failed Constraints: ['enum_mismatch:priority', 'const:status:active→enabled']

Recommendations: ["Remove ['critical', 'urgent'] from property 'priority' enum or expand consumer enum", "Change property 'status' const from 'active' to 'enabled'"]
```

**Features:**
- **Specific violation detection**: Identifies exactly which constraints fail
- **Property-level analysis**: Shows which object properties cause incompatibilities
- **Actionable recommendations**: Concrete steps to fix schema mismatches
- **Constraint labeling**: Clear labels for failed constraints (e.g., `enum_mismatch:priority`)
- **Real counterexamples**: Meaningful JSON values that demonstrate incompatibility

## 🔧 Architecture

jSound implements the specification in `docs/json-schema-to-z3-spec.md` with these key components:

### Core Components

1. **JSON Encoding** (`src/jsound/core/json_encoding.py`)
   - Defines Z3 JSON datatype with tagged union
   - Handles type predicates and mutual exclusion constraints
   - Manages finite key universes for objects

2. **Schema Compiler** (`src/jsound/core/schema_compiler.py`)
   - Compiles JSON Schema keywords to Z3 predicates
   - Supports: `type`, `const`, `enum`, boolean composition (`allOf`, `anyOf`, `oneOf`, `not`)
   - Basic support for objects, arrays, strings, numbers

3. **Subsumption Checker** (`src/jsound/core/subsumption.py`)
   - Main engine that sets up Z3 solver
   - Checks `P ∧ ¬C` satisfiability
   - Handles solver timeouts and configurations

4. **Witness Extractor** (`src/jsound/core/witness.py`)
   - Extracts counterexamples from Z3 models
   - Reconstructs JSON values from SMT solutions

### Supported JSON Schema Features

**✅ Currently Supported:**
- **Basic types**: `null`, `boolean`, `integer`, `number`, `string`, `array`, `object`
- **Constants**: `const`, `enum` with enhanced mismatch explanations
- **Boolean composition**: `allOf`, `anyOf`, `oneOf`, `not`
- **Type unions**: `"type": ["string", "number"]`
- **Object properties**: `properties`, `required`, `additionalProperties`, `patternProperties`
- **Array constraints**: `items`, `minItems`, `maxItems`, `contains`, `uniqueItems`
- **String constraints**: `minLength`, `maxLength`, `pattern`, `format`
- **Number constraints**: `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`
- **Dependencies**: `dependentRequired`, `dependentSchemas`, `dependencies` (legacy)
- **Conditionals**: Basic `if`/`then`/`else` support
- **References**: `$ref` with bounded unrolling
- **Enhanced explanations**: Detailed failure analysis with actionable recommendations

**🚧 Advanced Features (Not yet implemented):**
- Complex conditionals and nested `if`/`then`/`else`
- `unevaluatedProperties`, `unevaluatedItems`
- `contentEncoding`, `contentMediaType`
- `propertyNames` validation

## 🧪 Examples

### Example 1: API Versioning

**Producer (API v1):**
```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer", "minimum": 0}
  },
  "required": ["name", "age"]
}
```

**Consumer (API v2):**
```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "age": {"type": "integer"}
  },
  "required": ["name"]
}
```

Result: **Compatible** ✅ (v1 is more restrictive than v2)

### Example 2: Message Queue

**Producer (strict message format):**
```json
{"type": "string", "pattern": "^MSG-[0-9]+$"}
```

**Consumer (loose message format):**
```json
{"type": "string"}
```

Result: **Compatible** ✅ (producer messages will always validate against consumer)

### Example 3: Incompatible Types

**Producer:**
```json
{"type": ["string", "number"]}
```

**Consumer:**
```json
{"type": "boolean"}
```

Result: **Incompatible** ❌ (counterexample: any string or number)

### Programmatic Usage

jSound can also be used as a Python library:

```python
from jsound.api import JSoundAPI

# Initialize the API
api = JSoundAPI()

# Check subsumption
result = api.check_subsumption(producer_schema, consumer_schema)

if result.is_compatible:
    print("✓ Schemas are compatible")
else:
    print(f"✗ Incompatible: {result.explanation}")
    print(f"Counterexample: {result.counterexample}")
    print(f"Recommendations: {result.recommendations}")
```

**Enhanced API usage:**
```python
from jsound.enhanced_api import JSoundEnhancedAPI

# Enable enhanced explanations
api = JSoundEnhancedAPI(explanations=True)
result = api.check_subsumption(producer_schema, consumer_schema)

# Access detailed analysis
print(f"Failed constraints: {result.failed_constraints}")
print(f"Solver time: {result.solver_time}s")
```

## 🏗️ Development

### Project Structure

```
src/jsound/
├── __init__.py
├── main.py                  # CLI entry point
├── cli/
│   ├── __init__.py
│   └── commands.py          # CLI command definitions
├── core/
│   ├── __init__.py
│   ├── json_encoding.py     # Z3 JSON datatype definitions
│   ├── schema_compiler.py   # JSON Schema → Z3 predicate compilation
│   ├── subsumption.py       # Main subsumption checking logic
│   └── witness.py           # Model → JSON counterexample extraction
├── utils/
│   ├── __init__.py
│   └── bounds.py            # Finite universe and bounds management
└── exceptions.py            # Custom exceptions
```

### Running Tests

jSound has comprehensive test coverage (99.3%) across all features:

```bash
# Run all tests
pytest

# Run specific test suites
pytest tests/test_dependencies.py          # Dependency constraints
pytest tests/test_const_enum_enhanced.py   # Const/enum explanations
pytest tests/test_pattern_properties.py    # Pattern properties
pytest tests/test_unique_items.py          # Array uniqueness
pytest tests/test_oneof.py                 # OneOf constraints

# Test CLI functionality
jsound examples/producer.json examples/consumer.json

# Test enhanced explanations
jsound --explanations examples/ecommerce_product_v1.json examples/ecommerce_product_v2_breaking.json
```

### Example Test Output

```bash
$ pytest -v
============================= test session starts ==============================
collecting ... collected 89 items

tests/test_dependencies.py::TestDependencies::test_dependent_required_basic PASSED
tests/test_const_enum_enhanced.py::TestConstEnumEnhanced::test_const_mismatch PASSED
tests/test_pattern_properties.py::TestPatternProperties::test_pattern_mismatch PASSED
...

============================== 89 passed in 2.34s ==============================
```

### Configuration

Default bounds can be adjusted via CLI options:

- **Array bounds**: `--max-array-length` (default: 50)
- **Recursion depth**: `--max-recursion-depth` (default: 3)
- **Solver timeout**: `--timeout` (default: 30 seconds)

## 🎓 Theory

jSound implements the **JSON Schema → SMT** translation specified in `docs/json-schema-to-z3-spec.md`. Key theoretical foundations:

1. **Finite Model Property**: Uses bounded arrays and finite key universes to ensure decidability
2. **Tagged Union Encoding**: JSON values encoded as Z3 algebraic datatypes
3. **Subsumption as Satisfiability**: P ⊆ C iff P ∧ ¬C is unsatisfiable
4. **Counterexample Extraction**: SAT models converted back to concrete JSON instances

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📝 License

Copyright 2024 Scidonia Limited

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## 🙋 FAQ

**Q: What JSON Schema version is supported?**
A: jSound targets JSON Schema Draft 2019-09 core features, with focus on practical subset for API compatibility checking.

**Q: How does jSound handle infinite schemas?**
A: jSound uses finite bounds (configurable array lengths, recursion depth) to ensure termination while maintaining soundness within those bounds.

**Q: Can I use jSound in CI/CD pipelines?**
A: Yes! jSound provides machine-readable JSON output and meaningful exit codes perfect for automated workflows.

**Q: What happens if Z3 times out?**
A: jSound reports the timeout as an error with exit code 2. Increase `--timeout` or simplify schemas.

**Q: How accurate are the counterexamples?**
A: Counterexamples are guaranteed to satisfy the producer schema but violate the consumer schema, providing concrete evidence of incompatibility.

**Q: I'm getting "Z3 library not found" errors. How do I fix this?**
A: Make sure Z3 is properly installed:
- Try `pip install z3-solver` for the Python package
- On Linux: `sudo apt-get install libz3-dev z3`
- On macOS: `brew install z3`
- Verify with: `python -c "import z3; print('Z3 working!')"`

**Q: Does jSound work on Windows?**
A: Yes! Install Z3 via conda (`conda install -c conda-forge z3`) or download from GitHub releases, then `pip install jsound`.

**Q: What's the difference between the CLI and programmatic API?**
A: The CLI is great for scripts and CI/CD. The programmatic API gives you structured access to results, enhanced explanations, and integration into Python applications.
