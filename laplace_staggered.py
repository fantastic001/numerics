
import scipy 
import scipy.sparse
import scipy.sparse.linalg
import numpy as np 

n = 100
r = c = 0
A = scipy.sparse.lil_matrix((n**2, n**2))

solids = np.zeros([n,n])

def K1(n, a11):
    """
    If a11 is 1 then matrix is suited for Neumann boundary conditions (pressure)
    If a11 is 2 then Dirchlet is used 
    If a11 is 3 then Dirchlet is used but for middle condition 
    """
    a = np.zeros(n-1)
    b = np.zeros(n)
    c = np.zeros(n-1)

    a.fill(-1)
    b[1:-1] = 2
    b[[0, -1]] = a11
    c.fill(-1)
    s = scipy.sparse.diags([a,b,c], [-1, 0, 1])
    return s

# Laplacian operators are computed as negative value of true laplacian operator 
# for pressure solution, then, it should be used like this: P = scipy.sparse.linalg.spsolve(-Lp, rhs)
# for diffusion, use u = scipy.sparse.linalg.spsolve(Lx, rhs)


def boundary_left(i,j):
    return j == 0 or solids[i,j-1] 
def boundary_right(i,j):
    return j == c-1 or solids[i,j+1] 
def boundary_up(i,j):
    return i == 0 or solids[i-1,j] 
def boundary_down(i,j):
    return i == r-1 or solids[i+1,j] 

SI = scipy.sparse.eye(n)
Lp = scipy.sparse.kron(SI, K1(n, 1)) + scipy.sparse.kron(K1(n, 1), SI)
c = r = n
for i in range(r):
    for j in range(c):
        c = n
        s = i*c + j
        Lp[s,s] = 0
        if not boundary_up(i,j):
            Lp[s,s] += 1
            Lp[s,s-c] = -1
        if not boundary_down(i,j):
            Lp[s,s] += 1
            Lp[s,s+c] = -1
        if not boundary_right(i,j):
            Lp[s,s] += 1
            Lp[s,s+1] = -1
        if not boundary_left(i,j):
            Lp[s,s] += 1
            Lp[s,s-1] = -1

Lp[0,0] = 1.5 * Lp[0,0]
psolver = scipy.sparse.linalg.splu(Lp)


viscosity = 1e-06
dt = 0.1
SI_ = scipy.sparse.eye(n*(n-1))
SI__= scipy.sparse.eye(n-1)

Lxx = scipy.sparse.kron(SI,K1(n-1,2)) + scipy.sparse.kron(K1(n,3),SI__)
Lx = SI_ + (viscosity*dt)*Lxx
(r,c) = (n-1, n)
for i in range(r):
    for j in range(c):
        s = i*c + j
        Lx[s,s] = 4
        if not boundary_up(i,j):
            Lx[s,s] = 5
            Lx[s,s-c] = -1
        if not boundary_down(i,j):
            Lx[s,s] = 5
            Lx[s,s+c] = -1
        if not boundary_right(i,j):
            Lx[s,s+1] = -1
        if not boundary_left(i,j):
            Lx[s,s-1] = -1
xsolver = scipy.sparse.linalg.splu(Lx)

Lyy = scipy.sparse.kron(SI__,K1(n,3)) + scipy.sparse.kron(K1(n-1,2),SI)
Ly = SI_ + (viscosity*dt)*Lyy
(r,c) = (n,n-1)
for i in range(r):
    for j in range(c):
        c = n - 1
        s = i*c + j
        Ly[s,s] = 4
        if not boundary_up(i,j):
            Ly[s,s] = 5
            Ly[s,s-c] = -1
        if not boundary_down(i,j):
            Ly[s,s] = 5
            Ly[s,s+c] = -1
        if not boundary_right(i,j):
            Ly[s,s+1] = -1
        if not boundary_left(i,j):
            Ly[s,s-1] = -1
ysolver = scipy.sparse.linalg.splu(Ly)

# ------ Grid manipulation functions ------

def reset_solids(u,v):
    for i in range(n):
        for j in range(n):
            if solids[i,j]:
                u[i-1,j] = 0 
                u[i,j] = 0 
                v[i,j-1] = 0 
                v[i,j] = 0
    return (u,v) 

def to_centered(u,v):
    """
    u,v have to be transposed and with boundaries attached

    Use attach_boundaries(...) for attaching boundaries 
    """
    return ((u[:-1, :] + u[1:, :])/2, (v[:,:-1] + v[:,1:])/2)

def to_staggered(u,v):
    """
    Converts centered field to staggered field

    Returns staggered field WITHOUT boundaries
    """
    uc, vc = ((u[:-1, :] + u[1:, :])/2, (v[:,:-1] + v[:,1:])/2)
    uc[[0, -1],:] = 2*u[[0, -1], :]
    vc[:,[0, -1]] = 2*v[:, [0, -1]]
    return (uc, vc)

def field_transpose(u,v):
    return (u.T, v.T)


# ------ Following functions are suited for transposed grid (i.e. first index is x direction, second index is y direction) ------

def attach_boundaries(u,v):
    """
    Adds boundary nodes to x-component and y-component 

    u,v are transposed fields 
    """
    p = np.zeros([n+1,n])
    q = np.zeros([n, n+1])
    p[1:-1,:] = u
    q[:, 1:-1] = v
    return (p,q)

def compute_divergence(u,v):
    """
    Computes divergence 

    Fields must have boundaries attached by attach_boundaries(u,v)
    """
    return np.diff(u.T).T + np.diff(v)

def apply_pressure(u,v,p):
    """
    WARNING: Pressure must be negative such that it is computed from p = psolver.solve(rhs) not p = -psolver.solve(rhs)
    """
    return (u + np.diff(p.T).T, v + np.diff(p))

def projection(u,v):
    ubc, vbc = attach_boundaries(u,v)
    rhs = compute_divergence(ubc, vbc).reshape(n**2)
    p = psolver.solve(rhs).reshape([n,n])
    u,v = apply_pressure(u,v,p)
    return (u,v)

x,y = np.mgrid[0:n, 0:n] # suited for transposed grid 


def boundary_count(i,j):
    s = 4
    if i == 0:
        s-=1
    if i == n-1:
        s-=1
    if j == 0:
        s-=1
    if j==n-1:
        s-=1
    return s

for i in range(n):
    for j in range(n):
        print((i,j))
        s = i*n + j 
        A[s,s] = -boundary_count(i,j)
        if i == 0:
            A[s,s+n] = 1
        if i == n-1:
            A[s,s-n] = 1
        if j == 0:
            A[s,s+1] = 1
        if j==n-1:
            A[s,s-1] = 1


print("Computation of A finished")
