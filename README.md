# JSond - JSON Schema Subsumption Checker

JSond is a tool that checks **JSON Schema subsumption** using Z3 SMT solver. It determines whether one JSON schema is compatible with another by checking if the producer schema is a subset of the consumer schema.

## 🎯 What is Schema Subsumption?

Given two JSON schemas P (producer) and C (consumer), we say **P ⊆ C** (P subsumes C) if every JSON document that validates against P also validates against C. 

JSond checks this by solving: **P ∧ ¬C is UNSAT**
- If **UNSAT**: Schemas are compatible (P ⊆ C)  
- If **SAT**: Schemas are incompatible, and JSond provides a counterexample

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Nix (for Z3 library dependencies)
- uv (for dependency management)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd jsound
```

2. Set up the environment:
```bash
direnv allow  # Sets up Nix environment with Z3
uv sync       # Install Python dependencies
```

3. Run JSond:
```bash
# Using the convenient wrapper script
./jsound producer_schema.json consumer_schema.json

# Or with uv directly (need to set Z3 library path)
export LD_LIBRARY_PATH=/nix/store/5z32bk36clikx62822is7rx80s61y7r5-z3-4.15.4-lib/lib:$LD_LIBRARY_PATH
uv run jsound producer_schema.json consumer_schema.json
```

## 📖 Usage Examples

### Basic Usage

```bash
# Check if producer schema is compatible with consumer schema
./jsound examples/producer.json examples/consumer.json

# Or using uv run (with Z3 library path)
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
./jsound [OPTIONS] PRODUCER_SCHEMA_FILE CONSUMER_SCHEMA_FILE

Options:
  --max-array-length INTEGER     Maximum array length for bounds [default: 50]
  --max-recursion-depth INTEGER  Maximum $ref unrolling depth [default: 3]  
  --timeout INTEGER              Z3 solver timeout in seconds [default: 30]
  --output-format TEXT           Output format: json, pretty, or minimal [default: pretty]
  --counterexample-file PATH     Save counterexample to file
  --verbose                      Enable verbose output
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

## 🔧 Architecture

JSond implements the specification in `json-schema-to-z3-spec.md` with these key components:

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
- Basic types: `null`, `boolean`, `integer`, `number`, `string`, `array`, `object`
- Constants: `const`, `enum`
- Boolean composition: `allOf`, `anyOf`, `oneOf`, `not`
- Type unions: `"type": ["string", "number"]`

**🚧 Planned:**
- Object properties: `properties`, `required`, `additionalProperties`
- Array constraints: `items`, `minItems`, `maxItems`
- String constraints: `minLength`, `maxLength`, `pattern`
- Number constraints: `minimum`, `maximum`, `multipleOf`
- Conditionals: `if`/`then`/`else`
- References: `$ref` with bounded unrolling

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

```bash
# Test Z3 integration
python test_z3.py

# Test full subsumption pipeline  
python test_subsumption.py

# Test CLI functionality
./jsound examples/producer.json examples/consumer.json
```

### Configuration

Default bounds can be adjusted via CLI options:

- **Array bounds**: `--max-array-length` (default: 50)
- **Recursion depth**: `--max-recursion-depth` (default: 3)  
- **Solver timeout**: `--timeout` (default: 30 seconds)

## 🎓 Theory

JSond implements the **JSON Schema → SMT** translation specified in `json-schema-to-z3-spec.md`. Key theoretical foundations:

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

[License information here]

## 🙋 FAQ

**Q: What JSON Schema version is supported?**
A: JSond targets JSON Schema Draft 2019-09 core features, with focus on practical subset for API compatibility checking.

**Q: How does JSond handle infinite schemas?**
A: JSond uses finite bounds (configurable array lengths, recursion depth) to ensure termination while maintaining soundness within those bounds.

**Q: Can I use JSond in CI/CD pipelines?**  
A: Yes! JSond provides machine-readable JSON output and meaningful exit codes perfect for automated workflows.

**Q: What happens if Z3 times out?**
A: JSond reports the timeout as an error with exit code 2. Increase `--timeout` or simplify schemas.

**Q: How accurate are the counterexamples?**
A: Counterexamples are guaranteed to satisfy the producer schema but violate the consumer schema, providing concrete evidence of incompatibility.