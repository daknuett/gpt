#!/usr/bin/env python3
#
# Authors: Daniel Richtmann 2020
#          Christoph Lehner 2020
#
# Desc.: Test constructed coarse and coarse coarse operator against naive chained application
#
import gpt as g
import numpy as np
import sys

# command line parameters
grid_f_size = g.default.get_ivec("--fgrid", [8, 8, 8, 16], 4)
grid_c_size = g.default.get_ivec("--cgrid", [4, 4, 4, 8], 4)
grid_cc_size = g.default.get_ivec("--ccgrid", [2, 2, 2, 4], 4)

# setup rng, make it quiet
g.default.set_verbose("random", False)
rng = g.random("test")

# setup fine link fields
U = g.qcd.gauge.random(g.grid(grid_f_size, g.double), rng)

# do everything in single precision
U = g.convert(U, g.single)

# setup grids
grid_f = U[0].grid
grid_c = g.grid(grid_c_size, grid_f.precision)
grid_cc = g.grid(grid_cc_size, grid_f.precision)

# setup fine matrix
mat_f = g.qcd.fermion.wilson_clover(
    U,
    {
        "kappa": 0.137,
        "csw_r": 0,
        "csw_t": 0,
        "xi_0": 1,
        "nu": 1,
        "isAnisotropic": False,
        "boundary_phases": [1.0, 1.0, 1.0, 1.0],
    },
)

# number of basis vectors
nbasis_f = 20
nbasis_c = 30

# number of block orthogonalization steps
northo = 1

# define check tolerances
tol_ortho = 1e-28 if grid_f.precision == g.double else 1e-11
tol_links = 1e-30 if grid_f.precision == g.double else 1e-13
tol_operator = 1e-30 if grid_f.precision == g.double else 1e-13

# setup fine basis
basis_f = [g.vspincolor(grid_f) for __ in range(nbasis_f)]
rng.cnormal(basis_f)

# split fine basis into chiral halfs
g.split_chiral(basis_f)

# setup fine block map map
bm_f = g.block.map(grid_c, basis_f)

# orthonormalize fine basis
for i in range(northo):
    g.message("Block ortho step %d" % i)
    bm_f.orthonormalize()

# create coarse link fields
A_c = [g.mcomplex(grid_c, nbasis_f) for __ in range(9)]
Asaved_c = [g.mcomplex(grid_c, nbasis_f) for __ in range(9)]
g.coarse.create_links(
    A_c, mat_f, basis_f, {"make_hermitian": False, "savelinks": False}
)
g.coarse.create_links(
    Asaved_c, mat_f, basis_f, {"make_hermitian": False, "savelinks": True}
)

# compare link fields
for p in range(9):
    err2 = g.norm2(A_c[p] - Asaved_c[p]) / g.norm2(A_c[p])
    g.message(f"Relative deviation of Asaved_c[{p}] from A_c[{p}] = {err2:e}",)
    assert err2 <= tol_links
g.message(f"Tests for links passed for all directions")
del Asaved_c

# create coarse operator from links
mat_c = g.qcd.fermion.coarse(A_c, {"level": 0,},)

# setup coarse vectors
vec_in_c = g.vcomplex(grid_c, nbasis_f)
rng.cnormal(vec_in_c)

# apply chained and constructed coarse operator
vec_out_chained_c = g(bm_f.project * mat_f * bm_f.promote * vec_in_c)
vec_out_constructed_c = g(mat_c * vec_in_c)

# report error
err2 = g.norm2(vec_out_chained_c - vec_out_constructed_c) / g.norm2(vec_out_chained_c)
g.message(
    "Relative deviation of constructed from chained coarse operator on coarse grid = %e"
    % err2
)
assert err2 <= tol_operator
g.message("Test passed for coarse operator, %e <= %e" % (err2, tol_operator))

# Done with fine grid, now test on coarse #####################################

# setup coarse basis
basis_c = [g.vcomplex(grid_c, nbasis_f) for __ in range(nbasis_c)]
rng.cnormal(basis_c)

# split coarse basis into chiral halfs
g.split_chiral(basis_c)

# setup coarse block map map
bm_c = g.block.map(grid_cc, basis_c)

# orthonormalize coarse basis
for i in range(northo):
    g.message("Block ortho step %d" % i)
    bm_c.orthonormalize()

# create coarse coarse link fields
A_cc = [g.mcomplex(grid_cc, nbasis_c) for __ in range(9)]
Asaved_cc = [g.mcomplex(grid_cc, nbasis_c) for __ in range(9)]
g.coarse.create_links(
    A_cc, mat_c, basis_c, {"make_hermitian": False, "savelinks": False}
)
g.coarse.create_links(
    Asaved_cc, mat_c, basis_c, {"make_hermitian": False, "savelinks": True}
)

# compare link fields
for p in range(9):
    err2 = g.norm2(A_cc[p] - Asaved_cc[p]) / g.norm2(A_cc[p])
    g.message(f"Relative deviation of Asaved_cc[{p}] from A_cc[{p}] = {err2:e}",)
    assert err2 <= tol_links
g.message(f"Tests for links passed for all directions")
del Asaved_cc

# create coarse operator from links
mat_cc = g.qcd.fermion.coarse(A_cc, {"level": 1,},)

# setup coarse coarse vectors
vec_in_cc = g.vcomplex(grid_cc, nbasis_c)
rng.cnormal(vec_in_cc)

# apply chained and constructed coarse coarse operator
vec_out_chained_cc = g(bm_c.project * mat_c * bm_c.promote * vec_in_cc)
vec_out_constructed_cc = g(mat_cc * vec_in_cc)

# report error
err2 = g.norm2(vec_out_chained_cc - vec_out_constructed_cc) / g.norm2(
    vec_out_chained_cc
)
g.message(
    "Relative deviation of constructed from chained coarse coarse operator on coarse coarse grid = %e"
    % err2
)
assert err2 <= tol_operator
g.message("Test passed for coarse coarse operator, %e <= %e" % (err2, tol_operator))

# Done with chaining tests, now test ET against Grid on coarse grid ###########

# setup fields
rng.cnormal(A_c)
mat_c = g.qcd.fermion.coarse(A_c, {"level": 0,},)
vec_out_link_c, vec_out_mat_c = g.lattice(vec_in_c), g.lattice(vec_in_c)
vec_out_link_c[:] = 0.0
vec_out_link_c[:] = 0.0
rng.cnormal(vec_in_c)

# apply the link matrix
vec_out_link_c @= A_c[8] * vec_in_c
mat_c.Mdir(
    vec_out_mat_c, vec_in_c, 0, 0
)  # exploit the self coupling link, this uses Grid

# define check tolerance
tol = 0.0

# report error
diff2 = g.norm2(vec_out_link_c - vec_out_mat_c)
assert diff2 == tol
g.message("Test passed for coarse links, %e == %e" % (diff2, tol))

# Test ET against Grid on coarse coarse grid ##################################

# setup fields
rng.cnormal(A_cc)
mat_cc = g.qcd.fermion.coarse(A_cc, {"level": 1,},)
vec_out_link_cc, vec_out_mat_cc = g.lattice(vec_in_cc), g.lattice(vec_in_cc)
vec_out_link_cc[:] = 0.0
vec_out_link_cc[:] = 0.0
rng.cnormal(vec_in_cc)

# apply the link matrix
vec_out_link_cc @= A_cc[8] * vec_in_cc
mat_cc.Mdir(
    vec_out_mat_cc, vec_in_cc, 0, 0
)  # exploit the self coupling link, this uses Grid

# define check tolerance
tol = 0.0

# report error
diff2 = g.norm2(vec_out_link_cc - vec_out_mat_cc)
assert diff2 == tol
g.message("Test passed for coarse coarse links, %e == %e" % (diff2, tol))