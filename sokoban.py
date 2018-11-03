# #! /bin/env python
# #
# # Program, ktory nacita zadanie sudoku zo standartneho vstupu,
# # vyriesi ho (pomocou kniznice sudoku.py) a vypise riesenie
# # na standartny vystup.
# #
# # V linuxe ho mozete pustit napriklad:
# #
# # ./cv04io.py < sudoku.in
# #

# import sokoban.SokobanSolver
# import sys

# def die(msg):
#     sys.stderr.write('%s\n' % msg)
#     sys.exit(1)

# s = []
# try:
#     for line in sys.stdin:
#         if line.strip() != '':
#             row = [ int(x) for x in line.split() ]
#             if len(row) != 9:
#                 raise ValueError("Wrong line on input")
#             s.append(row)
#     if len(s) != 9:
#         raise ValueError("Wrong number of lines")
# except ValueError as e:
#     die('Error reading input: %s' % (e,))


# try:
#     sokoban = sokoban.SokobanSolver()
#     sokoban.solve('./maps/map1.txt')
# except e:
#     die('Error solving sudoku: %s' % (repr(e),))


# for row in result:
#     sys.stdout.write('%s\n' % ' '.join(map(str,row)))


# # vim: set sw=4 ts=4 sts=4 et :
