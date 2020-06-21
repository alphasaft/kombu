#!/home/louise/PycharmProjects/compilateur_SYNTHESE/venv/bin/python


from argparse import ArgumentParser
import os
import sys
from time import time
from editor import KomBuEditor
from KomBuInterpreter.Kompilers.KomBuKompiler import KomBuKompiler

# sys.argv = ['kombu', '-c', '-f', '/home/louise/KombuTests/BrainFuck/main.kb']


def parse_args():
    parser = ArgumentParser(prog='Kombu')
    parser.add_argument('-f', '--file', help="If the editor mode is choose, it's the file that'll be opened, else"
                                             "the kombu file to parse.")

    main_mode = parser.add_mutually_exclusive_group()
    main_mode.add_argument('-e', '--editor', action='store_true', help='open a kombu editor created with Tkinter.')
    main_mode.add_argument('-c', '--compile', action='store_true', help='compile the provided grammar file. Needs'
                                                                        ' --file option.')
    main_mode.add_argument('-p', '--project', help='Create a directory named PROJECT and a file main.kb inside.')

    output = parser.add_mutually_exclusive_group()
    output.add_argument('-o', '--output', help='Output for the compiled code.')
    output.add_argument('-d', '--display', action='store_true', help='Display the compiled code')
    output.add_argument('-x', '--execute', help="File which will be parsed by the created compiler")
    output.add_argument('-r', '--read', help="As --execute, but the parameter value is a string.")

    return parser.parse_args()


args = parse_args()
os.system('export PYTHONPATH=":/home/louise/anaconda3/lib/python3.7/site-packages"')

if args.editor:
    editor = KomBuEditor()
    editor.start(args.file or "main.kb" if "main.kb" in os.listdir() else None)

elif args.compile:

    if not args.file:
        raise SyntaxError('--compiler option needs a file to parse (--file option)')

    compiler = KomBuKompiler()
    base_lib_path = '/'.join(args.file.split('/')[:-1]) if args.file.startswith('/') else os.getcwd() + '/' + '/'.join(args.file.split('/')[:-1])
    filename = args.file.split('/')[-1]

    with open(args.file, 'r') as f:
        bef = time()
        compiled, properties = compiler.kompile(f.read(), base_lib_path, filename)
        aft = time()
    print("Successfully compiled (%s seconds)" % str(aft-bef))

    if args.display:
        print(compiled)
    elif args.output:
        with open(args.output, 'w') as f:
            f.write(compiled)
    elif args.execute:
        with open(args.execute) as f:
            compiled = compile(compiled.replace('[insert input here]', f.read()), '<Language-compiler>', 'exec')
            exec(compiled, locals(), locals())

    elif args.read:
        compiled = compile(compiled.replace('[insert input here]', args.read), '<Language-compiler>', 'exec')
        exec(compiled, locals(), locals())

elif args.project:
    result = os.system('mkdir {} > /dev/null 2>&1'.format(args.project))
    if result == 256:
        print("Project {} cannot be created ; It mights already exist".format(args.project))
    else:
        os.system('touch {}/main.kb'.format(args.project))
        os.system('cp -r /home/louise/PycharmProjects/KomBu-v1.0/kblibs {}'.format(args.project))

else:
    raise SyntaxError("Please chose a main mode (either -e (--editor) or -c (--compile)")
