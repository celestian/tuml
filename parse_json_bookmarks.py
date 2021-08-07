"""tuml

Usage:
  parse_json_bookmarks <bookmarks_file>

Options:
  -h --help             Show this screen.
"""

import json
from docopt import docopt


def find_tumblr(text):
    if 'tumblr' in text:
        #print(text)
        if 'https' in text:
            print(text[8:text.find('tumblr') - 1])
        else:
            print(text[7:text.find('tumblr') - 1])

def parse(chunk):
    for item in chunk:
        if 'children' in item:
            parse(item['children'])
        else:
            if 'uri' in item:
                find_tumblr(item['uri'])

def main():

    args = docopt(__doc__, version='0.0.1')

    f = open(args['<bookmarks_file>'])
    data = json.load(f)
    parse(data['children'])

    #print(json.dumps(data, indent=2, sort_keys=True))

    f.close()

if __name__ == '__main__':
    main()
