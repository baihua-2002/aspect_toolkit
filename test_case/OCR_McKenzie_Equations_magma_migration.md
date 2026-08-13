# An Introduction and Tutorial to the "McKenzie Equations" for magma migration

Marc Spiegelman, Richard Katz and Gideon Simpson

Lamont-Doherty Earth Obs. of Columbia University; Dept. of Applied Physics and Applied Mathematics, Columbia Univ.; Dept. of Theoretical Physics and Applied Mathematics, Cambridge University

January 13, 2007

## 1 Introduction

Magmatism is a fundamental feature of plate boundaries and an essential process controlling the geochemical evolution of the planet. Here we present a new formulation for the equations of magma migration in viscous materials as originally derived by McKenzie [1984]. We also present a set of well-understood special case problems that form a useful benchmark-suite for developing and testing new codes.

### 1.1 Dimensional equations for mass and momentum

The equations for conservation of mass and momentum for both phases can be written:

$$ \frac{\partial\rho_f\phi}{\partial t}+\nabla\cdot[\rho_f\phi\mathbf{v}]=\Gamma $$  (1.1)

$$ \frac{\partial\rho_s(1-\phi)}{\partial t}+\nabla\cdot[\rho_s(1-\phi)\mathbf{V}]=-\Gamma $$  (1.2)

$$ \phi(\mathbf{v}-\mathbf{V})=-\frac{K}{\mu}[\nabla P-\rho_f\mathbf{g}] $$  (1.3)

$$ \nabla P=\nabla\cdot(\eta[\nabla\mathbf{V}+\nabla\mathbf{V}^T])+\nabla[(\zeta-\frac{2}{3}\eta)\nabla\cdot\mathbf{V}]+\bar{\rho}\mathbf{g} $$  (1.4)

Where phi is porosity, rho_f, rho_s are the fluid and solid densities, v, V are the fluid and solid velocity fields, Gamma is the rate of mass transfer from solid to liquid, K is the permeability, mu is the melt viscosity, P is the fluid pressure and g is the acceleration due to gravity. eta, zeta are the shear and bulk viscosities of the solid.

Constitutive Relations: K ~ phi^n with n ~ 2-5. Solid shear viscosity eta is porosity weakening. Bulk viscosity zeta must become infinite in the limit phi -> 0.

## 2 A Better Formulation

Pressure decomposition: P = P_l + P_compaction + P*

Where P_l = rho_s^0 * g * z is lithostatic pressure, P_compaction = (zeta - 2*eta/3) * div(V) is compaction pressure, P* is dynamic pressure.

The dimensionless equations (after scaling by compaction length delta and separation flux phi_0*w_0):

$$ \frac{D\phi}{Dt}=(1-\phi_0\phi)\frac{\mathcal{P}}{\xi}+\Gamma $$  (2.11)

$$ -\nabla\cdot K\nabla\mathcal{P}+\frac{\mathcal{P}}{\xi}=\nabla\cdot K[\nabla P^*+\hat{\mathbf{g}}]+\Gamma\frac{\Delta\rho}{\rho_f} $$  (2.12)

$$ \nabla\cdot\mathbf{V}=\phi_0\frac{\mathcal{P}}{\xi} $$  (2.13)

$$ \nabla P^*=\nabla\cdot\eta(\nabla\mathbf{V}+\nabla\mathbf{V}^T)-\phi_0\phi\hat{\mathbf{g}} $$  (2.14)

Compaction length: delta = sqrt(K(phi_0)*(zeta + 4*eta/3) / mu)
Separation flux: phi_0*w_0 = K(phi_0)*Delta_rho*g / mu

## 3 Special Cases and Benchmark Problems

### 3.1 Zero porosity, no melting (Stokes Flow)

In the limit phi = 0 with no melting, equations reduce to incompressible Stokes flow:

div(V) = 0  (3.1)
grad(P*) = div(eta*(grad(V) + grad(V)^T))  (3.2)

Driven entirely by boundary conditions for solid velocity or stress.

### 3.2 Zero Permeability, no melting

Non-zero porosity but K = 0, Gamma = 0:

D(phi)/Dt = 0  (3.3)
P_compaction/xi = 0  (3.4)
div(V) = 0  (3.5)
grad(P*) = div(eta*(grad(V)+grad(V)^T)) - phi_0*phi*g_hat  (3.6)

Incompressible Stokes flow with buoyancy terms and passive advection of porosity.

### 3.3 Constant porosity, iso-viscous solid, no melting

phi = 1, K = 1, eta, xi constant, Gamma = 0. Reduces to incompressible Stokes:

div(V) = 0  (3.7)
grad(P*) = eta*nabla^2(V) - phi_0*k  (3.8)

Compaction pressure P = 0 everywhere. Melt velocity determined by V and P*.
Used by Spiegelman and McKenzie [1987] for analytic models of melt flow beneath mid-ocean ridges.

### 3.4 Magmatic Solitary Waves

Small porosity limit (phi_0 << 1), eta constant, xi = 1, Gamma = 0, K = phi^n:

D(phi)/Dt = P  (3.11)
-div(phi^n * grad(P)) + P = div(phi^n * g_hat)  (3.12)

Admit non-linear solitary waves in 1, 2 and 3 dimensions that propagate over a uniform porosity background with fixed form and constant speed. For 1-D waves, analytic solutions exist for all integer n (Barcilon and Richter 1986 for n=3).

### 3.5 Magmatic Shear Bands: Variable shear viscosity, no melting, no buoyancy

Gamma = 0, g_hat = 0, eta and xi = f(phi, V):

D(phi)/Dt = (1 - phi_0*phi)*P/xi  (3.13)
-div(K*grad(P)) + P/xi = div(K*grad(P*))  (3.14)
div(V) = phi_0*P/xi  (3.15)
grad(P*) = div(eta*(grad(V)+grad(V)^T))  (3.16)

Viscosity law: eta(phi, epsilon_dot) = eta_0 * exp(alpha*(phi - phi_0)) * epsilon_II^((1-n)/n)  (3.17)

Where alpha = -28 +/- 3 (porosity-weakening coefficient), epsilon_II is second invariant of strain rate, n is power-law exponent.

Boundary conditions: periodic in x. On boundary, w = W = 0.

### 3.6 2D/3D Ridge Models with Forced Adiabatic Melting

Full solution of Eqs. (2.11)-(2.14) with:

Gamma = rho_s * W * dF/dz  (3.18)

where W is solid upwelling velocity and F(z) is imposed melting function.

## References

- Barcilon and Lovera, 1989. Solitary waves in magma dynamics. J. Fluid Mech., 204:121-133.
- Barcilon and Richter, 1986. Non-linear waves in compacting media. J. Fluid Mech., 164:429-448.
- Katz, Spiegelman, and Holtzman, 2006. The dynamics of melt and shear localization in partially molten aggregates. Nature, 442:676-679.
- McKenzie, 1984. The generation and compaction of partially molten rock. J. Petrol., 25:713-765.
- Spiegelman, 1993a. Flow in deformable porous media. part 1. J. Fluid Mech., 247:17-38.
- Spiegelman, 1993b. Flow in deformable porous media. part 2. J. Fluid Mech., 247:39-63.
- Spiegelman and McKenzie, 1987. Simple 2-D models for melt extraction at mid-ocean ridges and island arcs. Earth Planet. Sci. Lett., 83:137-152.
- Scott and Stevenson, 1984. Magma solitons. Geophys. Res. Lett., 11:1161-1164.
- Stevenson, 1989. Spontaneous small-scale melt segregation in partial melts undergoing deformation. Geophys. Res. Lett., 16(9):1067-1070.
