from sympy.strategies.tree import (treeapply, treeapply, greedy, allresults,
        brute)
from sympy.core.compatibility import reduce
from functools import partial

def test_treeapply():
    tree = ([3, 3], [4, 1], 2)
    assert treeapply(tree, {list: min, tuple: max}) == 3

    add = lambda *args: sum(args)
    mul = lambda *args: reduce(lambda a, b: a*b, args, 1)
    assert treeapply(tree, {list: add, tuple: mul}) == 60

def test_treeapply_leaf():
    assert treeapply(3, {}, leaf=lambda x: x**2) == 9
    tree = ([3, 3], [4, 1], 2)
    treep1 = ([4, 4], [5, 2], 3)
    assert treeapply(tree, {list: min, tuple: max}, leaf=lambda x: x+1) == \
           treeapply(treep1, {list: min, tuple: max})

def test_treeapply_strategies():
    from sympy.strategies import chain, minimize
    join = {list: chain, tuple: minimize}
    inc = lambda x: x + 1
    dec = lambda x: x - 1
    double = lambda x: 2*x

    assert treeapply(inc, join) == inc
    assert treeapply((inc, dec), join)(5) == minimize(inc, dec)(5)
    assert treeapply([inc, dec], join)(5) == chain(inc, dec)(5)
    tree = (inc, [dec, double]) # either inc or dec-then-double
    assert treeapply(tree, join)(5) == 6
    assert treeapply(tree, join)(1) == 0

    maximize = partial(minimize, objective=lambda x: -x)
    join = {list: chain, tuple: maximize}
    fn = treeapply(tree, join)
    assert fn(4) == 6  # highest value comes from the dec then double
    assert fn(1) == 2  # highest value comes from the inc

def test_greedy():
    inc = lambda x: x + 1
    dec = lambda x: x - 1
    double = lambda x: 2*x
    tree = [inc, (dec, double)] # either inc or dec-then-double

    fn = greedy(tree, objective=lambda x: -x)
    assert fn(4) == 6  # highest value comes from the dec then double
    assert fn(1) == 2  # highest value comes from the inc

    tree = [inc, dec, [inc, dec, [(inc, inc), (dec, dec)]]]
    lowest = greedy(tree)
    assert lowest(10) == 8

    highest = greedy(tree, objective=lambda x: -x)
    assert highest(10) == 12

def test_allresults():
    inc = lambda x: x+1
    dec = lambda x: x-1
    double = lambda x: x*2
    square = lambda x: x**2

    assert set(allresults(inc)(3)) == set([inc(3)])
    assert set(allresults([inc, dec])(3)) == set([2, 4])
    assert set(allresults((inc, dec))(3)) == set([3])
    assert set(allresults([inc, (dec, double)])(4)) == set([5, 6])

def test_brute():
    inc = lambda x: x+1
    dec = lambda x: x-1
    square = lambda x: x**2
    tree = ([inc, dec], square)
    fn = brute(tree, lambda x: -x)

    assert fn(2) == (2 + 1)**2
    assert fn(-2) == (-2 - 1)**2

    assert brute(inc)(1) == 2
