import sys

"""
expected: P6A_T02
  18 - trip_id: None
  28 - trip_id: P5A_T01
  43 - trip_id: P5A_T02
 716 - trip_id: P6A_T02
i: 2021-12-08-07-04-tcrta-0
expected: D2_T01
  26 - trip_id: None
  63 - trip_id: DCW_T01
 916 - trip_id: D2_T01
  94 - trip_id: D4_T01
i: 2021-12-08-07-09-tcrta-0
expected: D1_T01
"""

EXPECTED_KEY = 'expected: '
TRIP_ID_KEY = '- trip_id: '
NAME_KEY = 'i: '

def main(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
        lines.append('i: sentinel')
        index = 0
        correct = 0
        incorrect = 0
        expected_trip_id = None
        name = None
        sum = 0
        items = 0

        while index < len(lines):
            line = lines[index].strip()
            index += 1
            #print(f'- line: {line}')

            if line.startswith(NAME_KEY):
                total = correct + incorrect

                if total > 0:
                    correct_pct = int(correct * 100 / total)
                    print(f'{name}: {correct_pct}%')
                    sum += correct_pct
                    items += 1

                correct = 0
                incorrect = 0
                name = line[len(NAME_KEY):]

            if line.startswith(EXPECTED_KEY):
                expected_trip_id = line[len(EXPECTED_KEY):]
                #print(f'- expected_trip_id: \'{expected_trip_id}\'')

            i = line.find(TRIP_ID_KEY)
            if i > 0:
                tok = line.split(' ')
                trip_id = tok[-1]
                #print(f'- trip_id: \'{trip_id}\'')
                count = int(tok[0])
                #print(f'- count: {count}')

                if trip_id == expected_trip_id:
                    correct += count
                else:
                    incorrect += count

        print(f'-----------------------------')
        print(f'                     avg: {int(sum / items)}%')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f'usage: {sys.argv[0]} <filename>')
        exit(1)

    main(sys.argv[1])
