import sys

def main():
    if len(sys.argv) < 2:
        return "not enough arguments"

    filename = sys.argv[1]
    with open(filename, 'a') as f:
        f.write('foo\n')


if __name__ == '__main__':
    main()
