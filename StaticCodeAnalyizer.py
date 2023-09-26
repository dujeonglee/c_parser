'''
Copyright 2023 Dujeong Lee (dujeong.lee82@gmail.com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''

'''File IO'''
import os
'''Code Parsing'''
import clang.cindex
'''Specify libclang.so / dll path if required.'''
## clang.cindex.Config.set_library_path('/usr/lib/x86_64-linux-gnu/')

'''Rendering'''
import graphviz

'''sample config'''
config = {
    # project name
    'project' : 'sample project',
    # target dir
    'dirs' : ['sample'],
    # target files
    'files' : ['code.c'],
    # build option
    'build_options' : ['-E', '-fsyntax-only', '-DMODULE', '-Isample'],
    # functions to exlcude from analysis
    'ignore_func_list' : ['likely', 'unlikely', 'WARN', 'WARN_ON', 'BUG', 'BUG_ON']
}

class Function:
    '''
    Function class
    '''

    def __init__(self, name):
        '''
        Initialize Function
        '''
        self.name = name
        self.callee = set()
        self.args = []
        self.code = ''

    def __str__(self):
        '''
        Print Function Object
        '''
        return f'Function: {self.name}\n' +f'Args:{[x for x in self.args]}\n' + f'callee: {self.callee}\n' + f'code: {self.code}\n'

class StaticCodeAnalyizerConfig:
    '''
    StaticCodeAnalyizerConfig class
    '''
    def __init__(self, /, project, dirs, files, build_options, ignore_func_list):
        '''
        Initialize StaticCodeAnalyizerConfig
        '''
        self.project = project
        self.dirs = set(dirs)
        self.files = set(files)
        self.build_options = build_options
        self.ignore_func_list = ignore_func_list

    def __str__(self):
        '''
        Print StaticCodeAnalyizerConfig Object
        '''
        return 'dirs: {0}\nfiles: {1}\nbuild_options: {2}\nignore_func_list: {3}\n'.format(self.dirs, self.files, self.build_options, self.ignore_func_list)

class StaticCodeAnalyizer:
    '''
    Static code analyzer for clang
    '''

    def __init__(self, /, config):
        '''
        Initialize StaticCodeAnalyizer
        '''
        self.__call_graph = {}
        self.__file_name = []
        self.__config = config

        '''find all src files in given dir'''
        self.__file_name = self.__get_files_in_directories(self.__config.dirs) | set(self.__config.files)

        '''Append individual files to fileName list if have any'''
        print(f'%d files are loaded' % (len(self.__file_name)))
        print(*self.__file_name, sep="\n")
        print()
        print(self.__config)
        print()

    def __get_files_in_directories(self, input_paths):
        '''
        Traverse all files in directories
        '''
        input_paths.add('')
        return set([os.path.join(dirpath, filename) 
                for path in input_paths if path != ''
                    for dirpath, *dirnames, filenames in os.walk(path) 
                        for filename in filenames if filename[-1] == 'c'])

    def __print_diagnostics(self, translation_unit):
        '''
        Print build error messages.
        User must fix all Error / Fatal to get correct result
        '''
        for diag in translation_unit.diagnostics:
            severity_level_to_string = ('Ignored', 'Note', 'Warning', 'Error', 'Fatal')
            print(f'{severity_level_to_string[diag.severity]}: {diag.spelling}')

            if diag.location.file is not None:
                print(f"Location: {diag.location.file.name}:{diag.location.line}:{diag.location.column}")
            else:
                print("Location: N/A")

            if diag.severity >= clang.cindex.Diagnostic.Error:
                return "Error:{diag.severity}"
            else: pass
        else: pass
        return "Pass"

    def __tokens(self, node):
        '''Post-order traverse'''
        reversed_list = reversed(list(node.get_children()))
        for child in reversed_list:
            yield from self.__tokens(child)
        else: pass
        yield node

    def __get_function_code_block(self, node):
        '''
        Get code block for function
        '''

        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            start_location = node.extent.start
            end_location = node.extent.end

            with open(node.location.file.name) as source_file:
                try:
                    source_lines = source_file.readlines()
                except Exception as e:
                    source_lines = None

            if source_lines != None:
                start_line = start_location.line - 1
                end_line = end_location.line
                code_block = ''.join(source_lines[start_line:end_line])
                return code_block.strip()
            else:
                return ''
        else: pass

    def __get_callees(self, l, func_name):
        '''
        Get code block for function
        '''
        for node in l:
            if node.kind == clang.cindex.CursorKind.CALL_EXPR and node.spelling not in self.__config.ignore_func_list:
                callee_name = node.spelling

                if func_name not in self.__call_graph:
                    self.__call_graph[func_name] = Function(func_name)
                else: pass

                caller_func = self.__call_graph[func_name]

                caller_func.callee.add(callee_name)
            else: pass
        else: pass

    def __get_functions(self, root):
        '''
        Traverse functions in code
        '''

        '''Found function declaration'''
        l = []
        for node in self.__tokens(root):
            l.append(node)

            '''Found function'''
            if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
                if node.spelling not in self.__config.ignore_func_list and node.location.file.name in [f for f in self.__file_name]:
                    func_name = node.spelling

                    if func_name not in self.__call_graph:
                        self.__call_graph[func_name] = Function(func_name)
                    else: pass
                    func = self.__call_graph[func_name]

                    '''Get function code block'''
                    func.code = self.__get_function_code_block(node)

                    '''Get function argument'''
                    for param in node.get_arguments():
                        func.args.append((param.type.spelling, param.displayname))
                    else: pass

                    '''Get callees'''
                    self.__get_callees(l, func_name)
                else: pass
                l.clear()
            else: pass
        else: pass

    def run(self):
        '''
        Run StaticCodeAnalyizer
        '''
        index = clang.cindex.Index.create()

        '''For all files given by user via dirs and files'''
        for f in self.__file_name:
            '''Parsing files'''
            print('*'*100)
            translation_unit = index.parse(f, args=[x for x in self.__config.build_options + [''] if x != ''])

            if not translation_unit:
                print(f'Fetal Error: Failed to parse the source file {f}.' )
                exit(-1)
            else: pass

            '''Check error'''
            if self.__print_diagnostics(translation_unit) != "Pass":
                print(f'Fetal Error: Failed to parse the source file {f}.' )
                print('*'*100)
                exit(-1)
            else: pass

            '''Traverse Abstract Syntax Tree(AST)'''
            root_cursor = translation_unit.cursor
            self.__get_functions(root_cursor)
            print(f'Completed {root_cursor.spelling}')
            print('*'*100)
        else: pass

    def show(self):
        '''
        Dump self.__call_graph
        '''

        for x in self.__call_graph.values():
            print(x)
        else: pass

    def render(self):
        '''
        Render self.__call_graph
        graphviz is required. (See: https://graphviz.org/download/)
        '''

        dot = graphviz.Digraph(comment=self.__config.project)
        for f in self.__call_graph.values():
            dot.node(f.name, f'{f.name}({", ".join([arg[0]+" "+arg[1] for arg in f.args]) if len(f.args) else "void"})')
        else: pass

        for caller in self.__call_graph.values():
            for callee in caller.callee:
                dot.edge(caller.name, callee)
            else: pass
        else: pass
        dot.render(self.__config.project.replace(' ', '_'), view=True)

def main():
    sca = StaticCodeAnalyizer(StaticCodeAnalyizerConfig(**config))
    sca.run()
    sca.show()
    sca.render()

if __name__ == "__main__":
    main()
