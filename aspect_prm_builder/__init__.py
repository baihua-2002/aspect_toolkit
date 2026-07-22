"""ASPECT .prm interactive middleware.

This package provides a structured, conversation-driven way to generate ASPECT
``.prm`` parameter files without requiring the LLM (or the user) to know the
exact ASPECT parameter syntax.

Public API:

* ``schema.build_schema()`` - parameter schema.
* ``engine.GuidedBuildSession`` - interactive conversation engine.
* ``engine.build_from_answers()`` - normalize a pre-populated answer dict.
* ``assembler.assemble_prm()`` / ``assembler.write_prm()`` - generate .prm files.
* ``validator.validate_answers()`` - lightweight validation.

Example:

    from aspect_prm_builder import engine, assembler
    answers = engine.build_from_answers({
        "Dimension": 2,
        "End time": 0.5,
        "Geometry model.Model name": "box",
        "Geometry model.Box.X extent": 1,
        "Geometry model.Box.Y extent": 1,
        "Material model.Model name": "simple",
        "Material model.Simple model.Viscosity": 1,
    })
    prm = assembler.assemble_prm(answers)
    print(prm)
"""

from . import assembler, engine, schema, validator

__all__ = ["assembler", "engine", "schema", "validator"]
