# Release notes for sbmlsim x.y.z
- breaking changes in units handling
- bugfix plotting `dimensionless` units in labels
- remove deprecated `distrib` and `sampling` functionality.

**parameter fitting**
- refactoring parameter fitting
- improved weight and options handling
- documentation  
- reports for parameter fitting (fit mapping contribution, #79)
- storing and combination of parameter fitting results (#73)
- better cost plots (#72)
- improved parameter fitting results plots (#96)
- loss functions implemented (#99)
  - ‘linear’ (default) : rho(z) = z. Gives a standard least-squares problem.
  - ‘soft_l1’ : rho(z) = 2 * ((1 + z)**0.5 - 1). The smooth approximation of l1 (absolute value) loss. Usually a good choice for robust least squares.
  - ‘cauchy’ : rho(z) = ln(1 + z). Severely weakens outliers influence, but may cause difficulties in optimization process.
  - ‘arctan’ : rho(z) = arctan(z). Limits a maximum loss on a single residual, has properties similar to ‘cauchy’.
    
