import os
from tkinter import Tk, Text, Toplevel, Button, IntVar, Entry, Frame, Checkbutton, PhotoImage, LEFT, RIGHT, TOP, BOTTOM
from KomBuInterpreter.Kompilers.KomBuKompiler import KomBuKompiler
from utils import catch_output


FONT = ('', 12)


class KomBuEditor(Tk):
    def __init__(self):

        self.save_list = []

        Tk.__init__(self)

        self._editor_frame = Text(master=self, bg='#2D3038', fg='white', height=25, width=131, undo=True)
        self._editor_frame.grid(row=1, column=2, columnspan=5)

        self._navigator = Frame(master=self, height=428, bg="white", width=230)
        self._navigator.grid(row=1, column=0, columnspan=2)

        self._compile_button = Button(master=self, command=self._compile, text='Compile', width=16, height=1)
        self._compile_button.grid(row=0, column=0)

        self._save_button = Button(master=self, command=self._save, text='Save', width=16, height=1)
        self._save_button.grid(row=0, column=1, columnspan=2)

        self._save_as_button = Button(master=self, command=self._save_as, text='Save as', width=16, height=1)
        self._save_as_button.grid(row=0, column=3)

        self._open_button = Button(master=self, command=self._open, text='Open', width=16, height=1)
        self._open_button.grid(row=0, column=4)

        self._quit_button = Button(master=self, command=self.shutdown, text='Quit', width=16, height=1)
        self._quit_button.grid(row=0, column=6)

        self._newfile_button = Button(master=self, command=self._create_file, text="New", width=16, height=1)
        self._newfile_button.grid(row=0, column=5)

        self._output = Text(master=self, bg='#9FAEB3', height=12, width=80, fg='black')
        self._output.grid(row=2, column=0, columnspan=5)

        self._verbose = IntVar()
        self._verbosity_checkbutton = Checkbutton(master=self, variable=self._verbose, text='Verbose output')
        self._verbosity_checkbutton.grid(row=3, column=0)

        self._test_zone = Text(master=self, bg='white', fg='black', height=12, width=80)
        self._test_zone.grid(row=2, column=5, columnspan=2)

        self._test_button = Button(master=self, command=self._test_code, text='Test', width=77, height=1)
        self._test_button.grid(row=3, column=5, columnspan=2)

        self._output_message = "Nothing to show"
        self._compiler_code = '!'
        self._compiler_properties = {}
        self._filepath = None

        self.bind_ctrls()

    def start(self, filepath=None):
        self._refresh()
        self.after(100, self._refresh)
        if filepath:
            self._open(filepath=filepath)
        self.update_navigator()
        Tk.mainloop(self)

    def shutdown(self, ctrl_event=None):

        self._save()
        self.destroy()

    def bind_ctrls(self):
        for ctrl, command in {

            "<Control-s>": self._save,
            "<Control-q>": self.shutdown,
            "<Control-Shift-S>": self._save_as,
            "<Control-o>": self._open,
            "<Control-x>": self._compile,
            "<Control-t>": self._test_code,

        }.items():

            self._editor_frame.bind(ctrl, command)

    def update_navigator(self):
        self._navigator = Frame(master=self, height=428, bg="white", width=230)
        self._navigator.grid(row=1, column=0, columnspan=2)

        if self._filepath:
            other_files = [f for f in os.listdir(self._current_directory_path()) if f.endswith('.kb')]
            for file in other_files:
                self._create_menu_entry(file)

    def _create_menu_entry(self, filename):
        Button(master=self._navigator, text='> '+filename, command=lambda: self._open(self._current_directory_path()+'/'+filename)).pack(side=TOP)

    def _put_end_characters(self, char):
        """This permits to insert the end character which correspond to CHAR after the cursor ; for example, if CHAR is
        '{', it will insert "}"."""

        to_insert = None
        if char == '{':
            to_insert = '{}'
        if char == "'":
            to_insert = "''"
        if char == '"':
            to_insert = '""'
        if char == '(':
            to_insert = '()'
        if char == '[':
            to_insert = '[]'

        if to_insert:
            self._editor_frame.insert(self._editor_frame.index('insert'), to_insert)
            self.event_generate('<Left>')
            return "break"

    def _compile(self, ctrl_event=None):
        compiler = KomBuKompiler()
        try:
            if self._filepath:
                self._compiler_code, self._compiler_properties = compiler.kompile(self._editor_frame.get('1.0', 'end'),
                                                                                  self._current_directory_path(), self._filepath.split('/')[-1])
            else:
                self._compiler_code, self._compiler_properties = compiler.kompile(self._editor_frame.get('1.0', 'end'),
                                                                     os.getcwd(), 'main.kb')
            self._output.configure(fg='black')

            if self._verbose.get():
                self._display(self._compiler_code)
            else:
                self._display("Compiled successfully.")

        except Exception as e:

            if len(str(e.__class__).split('.')) == 1:
                self._error(str(e.__class__)[8:-2] + ' : ' + str(e))
                self._compiler_code = '!'
                raise
            else:
                self._error(str(e.__class__).split('.')[-1][:-2] + ' : ' + str(e))
                self._compiler_code = '!'
                raise

    def _test_code(self):
        self._compile()
        if self._compiler_code == '!':
            self._error("No valid compiler is available to test your code.")
        else:
            try:
                self._output.configure(fg='black')
                with catch_output(self):
                    execute(self._test_zone.get('1.0', 'end'), self._compiler_properties['name'], self._compiler_code)

            except Exception as e:
                self._error('Test : ' + str(e))
                raise
            else:
                self._output_message += "\n\n" + "Code was tested successfully !"

    def _error(self, msg):
        self._output.configure(fg='red')
        self._output_message = msg

    def _display(self, msg):
        self._output.configure(fg='black')
        self._output_message = msg

    def _refresh(self):
        self._text_syntaxic_coloration()

        if str(self._output.get('0.0', 'end')) != self._output_message+'\n':
            self._output.delete('0.0', 'end')
            self._output.insert('end', self._output_message)

        self.after(100, self._refresh)

    def _text_syntaxic_coloration(self):
        self._editor_frame.tag_delete('red', '#0CB7EB', '#E69400', '#D8C437', 'green', 'grey', 'magenta')
        self._editor_frame.colorize('(inspect|return|with|from|ast|before|after)', '#E69400')
        self._editor_frame.colorize('//\*(.|\n)*?\*//', 'grey')
        self._editor_frame.colorize('//[^\n]*\n', 'grey')
        self._editor_frame.colorize('node \w+(\.\w+)*', '#D8C437')
        self._editor_frame.colorize('§\w+', "magenta")
        self._editor_frame.colorize('\$\w+', '#0CB7EB')
        self._editor_frame.colorize('<\w+?>', 'green')
        self._editor_frame.colorize('\'.*?\'', 'red')
        self._editor_frame.colorize('\".*?\"', 'red')
        self._editor_frame.colorize('/.*?/', 'red')
        self._editor_frame.colorize('&', '#0CB7EB')

    def _save(self, ctrl_event=None):
        if not self._filepath:
            self._save_as()
        else:
            try:
                with open(self._filepath, 'w') as f:
                    a = self._editor_frame.get('1.0', 'end')
                    f.write(a)
            except Exception as e:
                raise e
            else:
                self._display("Code correctly saved in file {}.".format(self._filepath))

    def _save_as(self, ctrl_event=None):

        def record_filepath():
            self._record_filepath(filepath_entry.get())
            get_filepath.destroy()
            self._save()

        get_filepath = Toplevel(master=self)
        get_filepath.title("Save as ...   ")
        sizing_frame = Frame(master=get_filepath, width=400, height=10)
        sizing_frame.pack()
        filepath_entry = Entry(master=sizing_frame)
        filepath_entry.pack()
        confirm = Button(master=sizing_frame, text='OK', command=record_filepath)
        confirm.pack()

    def _create_file(self, ctrl_event=None):

        def new_file():
            self._save()
            filename = filename_entry.get()
            if "/" in filename:
                self._error("File name needed, not file path.")
                return self._create_file()

            try:
                open(self._current_directory_path()+'/'+filename, 'x')
                self._open(self._current_directory_path()+'/'+filename)
                self.update_navigator()
            except Exception as e:
                self._error(e)

        get_filename = Toplevel(master=self)
        get_filename.title("New file")
        sizing_frame = Frame(master=get_filename, width=400, height=10)
        sizing_frame.pack()
        filename_entry = Entry(master=sizing_frame)
        filename_entry.pack()
        confirm = Button(master=sizing_frame, text='OK', command=new_file)
        confirm.pack()

    def _open(self, filepath=None, ctrl_event=None):

        def open_filepath(filepath=None):

            if not filepath:
                filepath = filepath_entry.get()
                if not filepath[-3:] == '.kb':
                    self._error("File {} is not a Kombu file.".format(filepath))
                    get_filepath.destroy()
                    return self._open()
                get_filepath.destroy()

            try:
                with open(filepath, 'r') as f:
                    self._editor_frame.delete('1.0', 'end')
                    self._editor_frame.insert('end', f.read())
            except (FileNotFoundError, IsADirectoryError):
                self._error("This file doesn't exist or is a directory.")
                self._open()
            else:
                self._record_filepath(filepath)
                self.update_navigator()
                self._display("File {} was correctly opened.".format(filepath))

        if self._filepath:
            self._save()

        if filepath:
            return open_filepath(filepath)

        get_filepath = Toplevel(master=self)
        get_filepath.title("Open ... ")
        filepath_entry = Entry(master=get_filepath)
        filepath_entry.pack()
        confirm = Button(master=get_filepath, text='OK', command=open_filepath)
        confirm.pack()

    def _record_filepath(self, filepath):
        if filepath.startswith('/'):
            self._filepath = filepath
        else:
            self._filepath = os.getcwd() + '/' + filepath

    def _current_directory_path(self):
        return "/".join(self._filepath.split("/")[:-1])


def colorize(self, regex, color):
    nmb_char = IntVar()
    last_pos = "1.0"
    while 1:
        last_pos = self.search(regex, index=last_pos, stopindex='end', regexp=1, count=nmb_char)
        if last_pos == "":
            break

        # Ajout d'un tag
        if not self.tag_names(last_pos):
            self.tag_add(color, last_pos, "%s + %d chars" % (last_pos, nmb_char.get()))
        last_pos = last_pos.split('.')[0] + '.' + str(int(last_pos.split('.')[1]) + nmb_char.get())

        self.tag_configure(color, foreground=color)


def execute(code, name, compiler):
    exec('global {0}Parser, {0}NodeWalker, {0}Compiler'.format(name))
    exec(compiler.replace('[insert input here]', code), locals(), locals())


Text.colorize = colorize
