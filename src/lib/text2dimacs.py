#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Converts "textual" CNF input into numeric dimacs SAT solver input.
#
# One clause per line, variable names must be sinle words.
# Logical ∨ and sinle letter v are ignored.
# Both minus sign (-) and negation symbol (¬) are supported for negation.
# Comments begin with the word "c".
#
# We do not check for errors like consecutive v's and similar.
#
# The input
#     kim v jim v sarah
#     -jim v kim
# gets translated to
#     1 2 3 0
#     -1 2 0
#

class VariableMap(dict):
    def maxVar(self):
        import functools
        return functools.reduce(max, self.values(), 0)
    def __missing__(self, key):
        val = self.maxVar() + 1
        self[key] = val
        return val

def translate(inf, outf):
    clauses = []
    varMap = VariableMap()
    with open(inf,'r') as f: 
        for line in f:
            clause = []
            tokens = line.split()
            if len(tokens) == 0 or tokens[0] == 'c':
                continue

            for w in line.split():
                if w in ['∨', 'v']:
                    continue

                neg  = w[0] in ['¬', '-']
                if neg:
                    w = w[1:]
                clause.append(varMap[w] * (-1 if neg else 1))

            clauses.append((line,clause))

    with open(outf,'w') as f:
        f.write('p cnf %d %d\n' % (varMap.maxVar(), len(clauses)))

        for line, clause in clauses:
            f.write('c %s' % line)
            f.write('%s 0\n' % ' '.join([str(x) for x in clause]))

    with open('variables.txt', 'w') as f:
        # dicts are hashed, so 'normal' order is not very nice
        for num, var in sorted([(num,var) for var,num in varMap.items()]):
            f.write('%d\n%s\n' % (num, var))


if __name__ == '__main__':
    import sys

    inf = sys.stdin
    if len(sys.argv) > 1:
        inf = open(sys.argv[1], 'r', encoding='utf-8')

    outf = sys.stdout
    if len(sys.argv) > 2:
        outf = open(sys.argv[2], 'w', encoding='utf-8')

    translate(inf, outf)

    if inf is not sys.stdin:
        inf.close()
    if outf is not sys.stdout:
        outf.close()

# vim: set sw=4 ts=4 sts=4 et :
