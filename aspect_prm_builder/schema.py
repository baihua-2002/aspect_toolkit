"""ASPECT .prm parameter schema.

This module defines the *structured* parameter space for ASPECT input files. The
schema is intentionally decoupled from the final .prm serialization so that an
LLM (or a human user) only has to answer a sequence of high-level, concrete
questions instead of memorizing ASPECT parameter syntax.

Design principles:

1. Hierarchical sections mirror ASPECT subsections (e.g. ``Geometry model`` ->
   ``Box``).
2. Every parameter declares a name, type, default, doc string, and optional
   dependencies so the engine knows when to ask for it.
3. The schema is data-driven: adding a new ASPECT plugin only requires adding
   new entries here, not rewriting the engine.

The schema is not exhaustive (ASPECT has hundreds of plugins), but it covers the
most common building blocks seen in the cookbooks and provides a generic
``RawParameter`` escape hatch for anything not yet catalogued.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

ParameterType = Union[
    "ScalarParameter",
    "BoolParameter",
    "ChoiceParameter",
    "ListParameter",
    "RawParameter",
    "Subsection",
]


@dataclass
class ScalarParameter:
    """A scalar parameter (float, int, string, or function expression)."""

    name: str
    doc: str
    default: Any = None
    value_type: str = "float"  # float | int | string
    required: bool = False

    def ask_text(self) -> str:
        default = ""
        if self.default is not None:
            default = f" [{self.default}]"
        return f"{self.name}{default}: {self.doc}"

    def parse(self, raw: str):
        raw = raw.strip()
        if raw == "":
            return self.default
        if self.value_type == "float":
            return float(raw)
        if self.value_type == "int":
            return int(raw)
        return raw


@dataclass
class BoolParameter:
    """A boolean parameter serialized as ``true`` / ``false``."""

    name: str
    doc: str
    default: bool = False
    required: bool = False

    def ask_text(self) -> str:
        return f"{self.name} [{'true' if self.default else 'false'}]: {self.doc}"

    def parse(self, raw: str) -> bool:
        raw = raw.strip().lower()
        if raw in ("", "default"):
            return self.default
        return raw in ("true", "yes", "y", "1", "on")


@dataclass
class ChoiceParameter:
    """A parameter whose value must be one of a fixed list of choices."""

    name: str
    doc: str
    choices: List[str]
    default: Optional[str] = None
    required: bool = True

    def ask_text(self) -> str:
        choices_str = ", ".join(f"'{c}'" for c in self.choices)
        default = f" [{self.default}]" if self.default else ""
        return f"{self.name}{default}: {self.doc} (choose one: {choices_str})"

    def parse(self, raw: str) -> str:
        raw = raw.strip()
        if raw == "" and self.default is not None:
            return self.default
        return raw


@dataclass
class ListParameter:
    """A comma-separated list of values (e.g. ``set List of postprocessors``)."""

    name: str
    doc: str
    default: List[str] = field(default_factory=list)
    value_type: str = "string"
    required: bool = False

    def ask_text(self) -> str:
        default = ", ".join(self.default) if self.default else ""
        return f"{self.name} [{default}]: {self.doc} (comma-separated list)"

    def parse(self, raw: str) -> List[str]:
        raw = raw.strip()
        if raw == "":
            return list(self.default)
        return [part.strip() for part in raw.split(",")]


@dataclass
class RawParameter:
    """Escape hatch for any parameter not yet in the typed schema.

    The value is taken verbatim. This is useful for experimental parameters or
    for rapidly bootstrapping a new ASPECT plugin without extending the schema.
    """

    name: str
    doc: str
    default: Any = ""
    required: bool = False

    def ask_text(self) -> str:
        default = f" [{self.default}]" if self.default != "" else ""
        return f"{self.name}{default}: {self.doc}"

    def parse(self, raw: str) -> str:
        raw = raw.strip()
        return raw if raw != "" else self.default


@dataclass
class Subsection:
    """A container of parameters and/or nested subsections."""

    name: str
    doc: str = ""
    parameters: List[ParameterType] = field(default_factory=list)
    optional: bool = False

    def ask_text(self) -> str:
        return f"Subsection: {self.name}"


# ---------------------------------------------------------------------------
# Convenience builders
# ---------------------------------------------------------------------------

def P(
    name: str,
    doc: str,
    default: Any = None,
    value_type: str = "float",
    required: bool = False,
) -> ScalarParameter:
    return ScalarParameter(name, doc, default, value_type, required)


def B(name: str, doc: str, default: bool = False) -> BoolParameter:
    return BoolParameter(name, doc, default)


def C(
    name: str,
    doc: str,
    choices: List[str],
    default: Optional[str] = None,
    required: bool = True,
) -> ChoiceParameter:
    return ChoiceParameter(name, doc, choices, default, required)


def L(
    name: str,
    doc: str,
    default: Optional[List[str]] = None,
    value_type: str = "string",
) -> ListParameter:
    return ListParameter(
        name, doc, default if default is not None else [], value_type
    )


def R(name: str, doc: str, default: Any = "") -> RawParameter:
    return RawParameter(name, doc, default)


def S(name: str, doc: str = "", parameters=None, optional: bool = False) -> Subsection:
    return Subsection(name, doc, parameters or [], optional)


# ---------------------------------------------------------------------------
# The ASPECT parameter schema
# ---------------------------------------------------------------------------

def build_schema() -> List[ParameterType]:
    """Return the canonical schema for the interactive builder.

    This schema is a curated subset of ASPECT parameters that appear in the
    cookbooks. It is designed to be extended by users/LLMs as new plugins are
    needed.
    """
    return [
        # Global parameters
        P(
            "Dimension",
            "Number of spatial dimensions",
            default=2,
            value_type="int",
            required=True,
        ),
        P(
            "Start time",
            "Start time of the simulation",
            default=0,
            value_type="float",
        ),
        P(
            "End time",
            "End time of the simulation",
            default=1,
            value_type="float",
        ),
        B(
            "Use years instead of seconds",
            "Use years as the unit of time",
            default=False,
        ),
        P(
            "Output directory",
            "Directory where output files are written",
            default="output",
            value_type="string",
        ),
        C(
            "Pressure normalization",
            "How to normalize the pressure",
            choices=["surface", "no", "volume"],
            default="surface",
            required=False,
        ),
        P(
            "Surface pressure",
            "Surface pressure value if pressure normalization is 'surface'",
            default=0,
            value_type="float",
        ),
        P(
            "CFL number",
            "CFL number used for time-stepping",
            default=1.0,
            value_type="float",
        ),
        P(
            "Maximum time step",
            "Maximum allowed time step",
            default=None,
            value_type="float",
        ),
        C(
            "Nonlinear solver scheme",
            "Nonlinear solver scheme",
            choices=[
                "single Advection, single Stokes",
                "iterated Advection and Stokes",
                "single Advection, iterated Stokes",
                "iterated Advection and iterated Stokes",
                "IMPES",
                "no Advection, iterated Stokes",
            ],
            default="single Advection, single Stokes",
            required=False,
        ),
        P(
            "Nonlinear solver tolerance",
            "Tolerance for the nonlinear solver",
            default=1e-5,
            value_type="float",
        ),
        P(
            "Max nonlinear iterations",
            "Maximum number of nonlinear iterations",
            default=100,
            value_type="int",
        ),
        P(
            "Adiabatic surface temperature",
            "Adiabatic surface temperature",
            default=None,
            value_type="float",
        ),
        P(
            "Additional shared libraries",
            "Comma-separated list of shared libraries to load",
            default="",
            value_type="string",
        ),
        # Geometry
        S(
            "Geometry model",
            "Define the geometry of the domain",
            [
                C(
                    "Model name",
                    "Geometry model",
                    choices=["box", "spherical shell", "chunk", "ellipsoidal chunk"],
                    default="box",
                ),
                S(
                    "Box",
                    "Parameters for a box geometry",
                    [
                        P("X extent", "Extent in x direction", default=1),
                        P("Y extent", "Extent in y direction", default=1),
                        P("Z extent", "Extent in z direction", default=1),
                        P(
                            "X repetitions",
                            "Number of initial cells in x direction",
                            default=1,
                            value_type="int",
                        ),
                        P(
                            "Y repetitions",
                            "Number of initial cells in y direction",
                            default=1,
                            value_type="int",
                        ),
                        P(
                            "Z repetitions",
                            "Number of initial cells in z direction",
                            default=1,
                            value_type="int",
                        ),
                    ],
                ),
                S(
                    "Spherical shell",
                    "Parameters for a spherical shell",
                    [
                        P(
                            "Inner radius",
                            "Inner radius of the shell",
                            default=3481000,
                        ),
                        P(
                            "Outer radius",
                            "Outer radius of the shell",
                            default=6336000,
                        ),
                    ],
                ),
            ],
        ),
        # Gravity
        S(
            "Gravity model",
            "Define the gravity field",
            [
                C(
                    "Model name",
                    "Gravity model",
                    choices=["vertical", "ascii data", "radial constant", "radial earth-like"],
                    default="vertical",
                ),
                S(
                    "Vertical",
                    "Parameters for vertical gravity",
                    [P("Magnitude", "Magnitude of gravity", default=9.81)],
                ),
            ],
        ),
        # Boundary velocity
        S(
            "Boundary velocity model",
            "Define velocity boundary conditions",
            [
                L(
                    "Tangential velocity boundary indicators",
                    "Boundaries with free tangential slip",
                    default=[],
                ),
                L(
                    "Zero velocity boundary indicators",
                    "Boundaries with zero velocity",
                    default=[],
                ),
                L(
                    "Prescribed velocity boundary indicators",
                    "Boundaries with prescribed velocity",
                    default=[],
                ),
                S(
                    "Function",
                    "Function expression for prescribed velocity",
                    [
                        P("Variable names", "Variables in the expression", default="x,z", value_type="string"),
                        P(
                            "Function constants",
                            "Constants used in the function expression",
                            default="",
                            value_type="string",
                        ),
                        P(
                            "Function expression",
                            "Mathematical expression for the velocity",
                            default="0; 0",
                            value_type="string",
                        ),
                    ],
                ),
            ],
        ),
        # Boundary temperature
        S(
            "Boundary temperature model",
            "Define temperature boundary conditions",
            [
                L(
                    "Fixed temperature boundary indicators",
                    "Boundaries with fixed temperature",
                    default=[],
                ),
                L(
                    "List of model names",
                    "List of boundary temperature models",
                    default=["box"],
                ),
                S(
                    "Box",
                    "Parameters for the box temperature model",
                    [
                        P("Bottom temperature", "Temperature at the bottom", default=1),
                        P("Top temperature", "Temperature at the top", default=0),
                        P("Left temperature", "Temperature at the left", default=0),
                        P("Right temperature", "Temperature at the right", default=0),
                    ],
                ),
                S(
                    "Spherical constant",
                    "Parameters for spherical constant temperature",
                    [
                        P("Inner temperature", "Temperature at the inner radius", default=1973),
                        P("Outer temperature", "Temperature at the outer radius", default=973),
                    ],
                ),
            ],
        ),
        # Boundary composition
        S(
            "Boundary composition model",
            "Define composition boundary conditions",
            [
                L(
                    "Fixed composition boundary indicators",
                    "Boundaries with fixed composition",
                    default=[],
                ),
                L(
                    "List of model names",
                    "List of boundary composition models",
                    default=["initial composition"],
                ),
            ],
        ),
        # Initial temperature
        S(
            "Initial temperature model",
            "Define initial temperature distribution",
            [
                C(
                    "Model name",
                    "Initial temperature model",
                    choices=["function", "adiabatic", "ascii data", "S40RTS perturbation", "spherical hexagonal perturbation"],
                    default="function",
                ),
                S(
                    "Function",
                    "Function expression for the initial temperature",
                    [
                        P("Variable names", "Variables in the expression", default="x,z", value_type="string"),
                        P(
                            "Function constants",
                            "Constants used in the function expression",
                            default="",
                            value_type="string",
                        ),
                        P(
                            "Function expression",
                            "Mathematical expression for the temperature",
                            default="0",
                            value_type="string",
                        ),
                    ],
                ),
            ],
        ),
        # Compositional fields
        S(
            "Compositional fields",
            "Define compositional fields",
            [
                P(
                    "Number of fields",
                    "Number of compositional fields",
                    default=0,
                    value_type="int",
                ),
                L(
                    "Names of fields",
                    "Names of the compositional fields",
                    default=[],
                ),
                L(
                    "Types of fields",
                    "Types of the compositional fields",
                    default=[],
                ),
                L(
                    "Compositional field methods",
                    "Advection method for compositional fields",
                    default=["field"],
                ),
                L(
                    "Mapped particle properties",
                    "Mapping of particle properties to fields",
                    default=[],
                ),
            ],
        ),
        # Initial composition
        S(
            "Initial composition model",
            "Define initial composition distribution",
            [
                C(
                    "Model name",
                    "Initial composition model",
                    choices=["function", "ascii data", "blob"],
                    default="function",
                ),
                S(
                    "Function",
                    "Function expression for the initial composition",
                    [
                        P("Variable names", "Variables in the expression", default="x,z", value_type="string"),
                        P(
                            "Function constants",
                            "Constants used in the function expression",
                            default="",
                            value_type="string",
                        ),
                        P(
                            "Function expression",
                            "Mathematical expression for the composition",
                            default="0",
                            value_type="string",
                        ),
                    ],
                ),
            ],
        ),
        # Material model
        S(
            "Material model",
            "Define material properties",
            [
                C(
                    "Model name",
                    "Material model",
                    choices=[
                        "simple",
                        "multicomponent",
                        "visco plastic",
                        "steinberger",
                        "latent heat",
                        "simple compressible",
                    ],
                    default="simple",
                ),
                S(
                    "Simple model",
                    "Parameters for the simple material model",
                    [
                        P("Reference density", "Reference density", default=1),
                        P("Reference specific heat", "Reference specific heat", default=1),
                        P("Reference temperature", "Reference temperature", default=0),
                        P("Thermal conductivity", "Thermal conductivity", default=1),
                        P(
                            "Thermal expansion coefficient",
                            "Thermal expansion coefficient",
                            default=1,
                        ),
                        P("Viscosity", "Constant viscosity", default=1),
                        P(
                            "Density differential for compositional field 1",
                            "Density change for compositional field 1",
                            default=None,
                        ),
                    ],
                ),
                S(
                    "Multicomponent",
                    "Parameters for the multicomponent material model",
                    [
                        P(
                            "Reference temperature",
                            "Reference temperature",
                            default=0,
                        ),
                        C(
                            "Viscosity averaging scheme",
                            "Viscosity averaging scheme",
                            choices=[
                                "arithmetic",
                                "harmonic",
                                "geometric",
                                "maximum composition",
                            ],
                            default="arithmetic",
                        ),
                        L(
                            "Viscosities",
                            "Viscosity of each component",
                            default=[],
                        ),
                        L(
                            "Densities",
                            "Density of each component",
                            default=[],
                        ),
                        L(
                            "Thermal conductivities",
                            "Thermal conductivity of each component",
                            default=[],
                        ),
                    ],
                ),
            ],
        ),
        # Formulation
        S(
            "Formulation",
            "Formulation of the governing equations",
            [
                C(
                    "Formulation",
                    "Formulation",
                    choices=[
                        "Boussinesq approximation",
                        "anelastic liquid approximation",
                        "truncated anelastic liquid approximation",
                        "isothermal compression",
                        "custom",
                    ],
                    default="Boussinesq approximation",
                ),
            ],
        ),
        # Mesh refinement
        S(
            "Mesh refinement",
            "Mesh refinement strategy",
            [
                P(
                    "Initial global refinement",
                    "Initial global refinement level",
                    default=2,
                    value_type="int",
                ),
                P(
                    "Initial adaptive refinement",
                    "Initial adaptive refinement steps",
                    default=0,
                    value_type="int",
                ),
                P(
                    "Time steps between mesh refinement",
                    "Frequency of adaptive mesh refinement",
                    default=0,
                    value_type="int",
                ),
                L(
                    "Strategy",
                    "List of refinement strategies",
                    default=[""],
                ),
                P(
                    "Coarsening fraction",
                    "Fraction of cells to coarsen",
                    default=0.05,
                    value_type="float",
                ),
                P(
                    "Refinement fraction",
                    "Fraction of cells to refine",
                    default=0.3,
                    value_type="float",
                ),
                P(
                    "Minimum refinement level",
                    "Minimum allowed refinement level",
                    default=None,
                    value_type="int",
                ),
                B(
                    "Normalize individual refinement criteria",
                    "Normalize individual refinement criteria",
                    default=False,
                ),
                P(
                    "Refinement criteria merge operation",
                    "How to combine multiple refinement criteria",
                    default="",
                    value_type="string",
                ),
                S(
                    "Minimum refinement function",
                    "Function-based minimum refinement level",
                    [
                        C(
                            "Coordinate system",
                            "Coordinate system for the function",
                            choices=["cartesian", "depth", "spherical"],
                            default="cartesian",
                        ),
                        P(
                            "Variable names",
                            "Variables in the expression",
                            default="x,y",
                            value_type="string",
                        ),
                        P(
                            "Function constants",
                            "Constants used in the function expression",
                            default="",
                            value_type="string",
                        ),
                        P(
                            "Function expression",
                            "Mathematical expression for the minimum refinement level",
                            default="0",
                            value_type="string",
                        ),
                    ],
                ),
            ],
        ),
        # Solver parameters
        S(
            "Solver parameters",
            "Linear and nonlinear solver settings",
            [
                P(
                    "Temperature solver tolerance",
                    "Tolerance for the temperature solver",
                    default=1e-10,
                    value_type="float",
                ),
                S(
                    "Stokes solver parameters",
                    "Stokes solver settings",
                    [
                        C(
                            "Stokes solver type",
                            "Stokes solver type",
                            choices=[
                                "block AMG",
                                "block GMG",
                                "direct solver",
                            ],
                            default="block AMG",
                        ),
                        P(
                            "Linear solver tolerance",
                            "Tolerance for the linear Stokes solver",
                            default=1e-6,
                            value_type="float",
                        ),
                        P(
                            "Number of cheap Stokes solver steps",
                            "Number of cheap Stokes solver steps",
                            default=4000,
                            value_type="int",
                        ),
                        P(
                            "GMRES solver restart length",
                            "GMRES restart length",
                            default=100,
                            value_type="int",
                        ),
                        B(
                            "Use full A block as preconditioner",
                            "Use full A block as preconditioner",
                            default=False,
                        ),
                    ],
                ),
            ],
        ),
        # Mesh deformation / free surface
        S(
            "Mesh deformation",
            "Free surface and mesh deformation",
            optional=True,
            parameters=[
                P(
                    "Mesh deformation boundary indicators",
                    "Boundary indicators and deformation types",
                    default="",
                    value_type="string",
                ),
                S(
                    "Free surface",
                    "Free surface parameters",
                    [
                        C(
                            "Surface velocity projection",
                            "Surface velocity projection",
                            choices=["normal", "vertical"],
                            default="vertical",
                        ),
                    ],
                ),
                S(
                    "Diffusion",
                    "Free surface diffusion parameters",
                    [
                        P(
                            "Hillslope transport coefficient",
                            "Hillslope transport coefficient",
                            default=1e-8,
                        ),
                    ],
                ),
                L(
                    "Additional tangential mesh velocity boundary indicators",
                    "Additional tangential mesh velocity boundaries",
                    default=[],
                ),
            ],
        ),
        # Particles
        S(
            "Particles",
            "Particle tracking parameters",
            optional=True,
            parameters=[
                P(
                    "Minimum particles per cell",
                    "Minimum particles per cell",
                    default=25,
                    value_type="int",
                ),
                P(
                    "Maximum particles per cell",
                    "Maximum particles per cell",
                    default=100,
                    value_type="int",
                ),
                C(
                    "Load balancing strategy",
                    "Load balancing strategy",
                    choices=[
                        "none",
                        "remove particles",
                        "add particles",
                        "remove and add particles",
                    ],
                    default="remove and add particles",
                ),
                L(
                    "List of particle properties",
                    "Tracked particle properties",
                    default=[],
                ),
                C(
                    "Interpolation scheme",
                    "Interpolation scheme",
                    choices=["linear least squares", "cell average", "bilinear least squares"],
                    default="cell average",
                ),
                C(
                    "Particle generator name",
                    "Particle generator name",
                    choices=["reference cell", "random uniform", "ascii file"],
                    default="reference cell",
                ),
                S(
                    "Generator",
                    "Particle generator parameters",
                    [
                        S(
                            "Reference cell",
                            "Reference cell generator parameters",
                            [
                                P(
                                    "Number of particles per cell per direction",
                                    "Number of particles per cell per direction",
                                    default=2,
                                    value_type="int",
                                )
                            ],
                        )
                    ],
                ),
            ],
        ),
        # Checkpointing
        S(
            "Checkpointing",
            "Checkpoint/restart parameters",
            optional=True,
            parameters=[
                P(
                    "Steps between checkpoint",
                    "Number of time steps between checkpoints",
                    default=50,
                    value_type="int",
                ),
                P(
                    "Time between checkpoint",
                    "Time between checkpoints",
                    default=0,
                    value_type="float",
                ),
            ],
        ),
        # Termination criteria
        S(
            "Termination criteria",
            "When to stop the simulation",
            optional=True,
            parameters=[
                L(
                    "Termination criteria",
                    "List of termination criteria",
                    default=["end time"],
                ),
                B(
                    "Checkpoint on termination",
                    "Write a checkpoint when the simulation terminates",
                    default=False,
                ),
            ],
        ),
        # Postprocess
        S(
            "Postprocess",
            "Output and postprocessing",
            [
                L(
                    "List of postprocessors",
                    "List of postprocessors to run",
                    default=["visualization", "velocity statistics", "temperature statistics"],
                ),
                S(
                    "Visualization",
                    "Visualization output parameters",
                    [
                        P(
                            "Time between graphical output",
                            "Time between graphical output",
                            default=0.01,
                        ),
                        C(
                            "Output format",
                            "Output file format",
                            choices=["vtu", "hdf5", "gnuplot", "dx"],
                            default="vtu",
                        ),
                        P(
                            "Number of grouped files",
                            "Number of grouped output files",
                            default=1,
                            value_type="int",
                        ),
                        L(
                            "List of output variables",
                            "Additional output variables",
                            default=[],
                        ),
                        B(
                            "Interpolate output",
                            "Interpolate output onto a refined grid",
                            default=False,
                        ),
                        S(
                            "Material properties",
                            "Material properties to output",
                            [
                                L(
                                    "List of material properties",
                                    "List of material properties to output",
                                    default=["density", "viscosity"],
                                ),
                            ],
                        ),
                    ],
                ),
                S(
                    "Depth average",
                    "Depth average output parameters",
                    [
                        P(
                            "Time between graphical output",
                            "Time between graphical output",
                            default=1e6,
                        ),
                        C(
                            "Output format",
                            "Output file format",
                            choices=["vtu", "hdf5", "gnuplot", "dx"],
                            default="vtu",
                        ),
                    ],
                ),
            ],
        ),
        # Heating model
        S(
            "Heating model",
            "Internal heating models",
            optional=True,
            parameters=[
                L(
                    "List of model names",
                    "List of heating models",
                    default=["compositional heating"],
                ),
                S(
                    "Compositional heating",
                    "Compositional heating parameters",
                    [
                        L(
                            "Use compositional field for heat production averaging",
                            "Flags for heat production averaging",
                            default=[],
                        ),
                        L(
                            "Compositional heating values",
                            "Heat production values per compositional field",
                            default=[],
                        ),
                    ],
                ),
            ],
        ),
        # Adiabatic conditions
        S(
            "Adiabatic conditions model",
            "Adiabatic reference profile",
            optional=True,
            parameters=[
                C(
                    "Model name",
                    "Adiabatic conditions model",
                    choices=["function", "ascii data", "initial profile"],
                    default="function",
                ),
            ],
        ),
        # Discretization
        S(
            "Discretization",
            "Discretization parameters",
            optional=True,
            parameters=[
                C(
                    "Composition polynomial degree",
                    "Polynomial degree for compositional fields",
                    choices=["1", "2", "3", "4"],
                    default="2",
                ),
                C(
                    "Temperature polynomial degree",
                    "Polynomial degree for temperature",
                    choices=["1", "2", "3", "4"],
                    default="2",
                ),
                C(
                    "Stokes velocity polynomial degree",
                    "Polynomial degree for Stokes velocity",
                    choices=["1", "2", "3", "4"],
                    default="2",
                ),
                C(
                    "Stokes pressure polynomial degree",
                    "Polynomial degree for Stokes pressure",
                    choices=["1", "2"],
                    default="1",
                ),
            ],
        ),
        # Raw escape hatch
        R(
            "raw_parameters",
            "Any additional raw parameters not covered by the schema. Provide as 'Section > Param = value' lines.",
            default="",
        ),
    ]


# ---------------------------------------------------------------------------
# Schema introspection helpers
# ---------------------------------------------------------------------------

def flatten_schema(
    schema: List[ParameterType],
    path: Tuple[str, ...] = (),
) -> List[Tuple[Tuple[str, ...], ParameterType]]:
    """Flatten the schema into a list of (path, parameter) pairs.

    This is useful for indexing and searching parameters.
    """
    result: List[Tuple[Tuple[str, ...], ParameterType]] = []
    for item in schema:
        if isinstance(item, Subsection):
            result.extend(flatten_schema(item.parameters, path + (item.name,)))
        else:
            result.append((path, item))
    return result


def get_parameter(
    schema: List[ParameterType], dotted_path: str
) -> Optional[ParameterType]:
    """Retrieve a parameter by its dotted path (e.g. ``Geometry model.Box.X extent``)."""
    parts = dotted_path.split(".")

    def _find(items, parts):
        if not parts:
            return None
        for item in items:
            if isinstance(item, Subsection):
                if item.name == parts[0]:
                    return _find(item.parameters, parts[1:])
            elif item.name == parts[0]:
                return item
        return None

    return _find(schema, parts)


def schema_to_json(schema: List[ParameterType]) -> List[Dict[str, Any]]:
    """Export the schema to a JSON-serializable structure.

    This is useful for LLM backends that prefer a JSON schema or for building
    web front-ends. The structure is a nested list of sections/parameters.
    """
    result: List[Dict[str, Any]] = []
    for item in schema:
        if isinstance(item, Subsection):
            result.append(
                {
                    "type": "subsection",
                    "name": item.name,
                    "doc": item.doc,
                    "optional": item.optional,
                    "parameters": schema_to_json(item.parameters),
                }
            )
        elif isinstance(item, ScalarParameter):
            result.append(
                {
                    "type": "scalar",
                    "name": item.name,
                    "doc": item.doc,
                    "value_type": item.value_type,
                    "default": item.default,
                    "required": item.required,
                }
            )
        elif isinstance(item, BoolParameter):
            result.append(
                {
                    "type": "bool",
                    "name": item.name,
                    "doc": item.doc,
                    "default": item.default,
                    "required": item.required,
                }
            )
        elif isinstance(item, ChoiceParameter):
            result.append(
                {
                    "type": "choice",
                    "name": item.name,
                    "doc": item.doc,
                    "choices": item.choices,
                    "default": item.default,
                    "required": item.required,
                }
            )
        elif isinstance(item, ListParameter):
            result.append(
                {
                    "type": "list",
                    "name": item.name,
                    "doc": item.doc,
                    "default": item.default,
                    "value_type": item.value_type,
                    "required": item.required,
                }
            )
        elif isinstance(item, RawParameter):
            result.append(
                {
                    "type": "raw",
                    "name": item.name,
                    "doc": item.doc,
                    "default": item.default,
                    "required": item.required,
                }
            )
    return result
