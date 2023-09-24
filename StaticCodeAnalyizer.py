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

config = {
    # project name
    'project' : 'sample project',
    # target dir
    'dirs' : ['sample'],
    # target files
    'files' : ['code.c'],
    # build option
    'build_options' : ['-E', '-fsyntax-only', '-DMODULE'],
    # include path
    'include_paths' : ['sample'],
    # functions to exlcude from analysis
    'ignore_func_list' : ['likely', 'unlikely', 'WARN', 'WARN_ON', 'BUG', 'BUG_ON'],
    # Any line with one of strs in ignore_lines is remove from tmp file.
    'ignore_lines' : ['EXPORT_SYMBOL',
                'EXPORT_SYMBOL_GPL',
                'module_init',
                'module_exit',
                'MODULE_LICENSE',
                'MODULE_AUTHOR',
                'MODULE_ALIAS_GENL_FAMILY',
                'MODULE_DESCRIPTION',
                'late_initcall',
                'pure_initcall',
                'core_initcall',
                'core_initcall_sync',
                'postcore_initcall',
                'postcore_initcall_sync',
                'arch_initcall',
                'arch_initcall_sync',
                'subsys_initcall',
                'subsys_initcall_sync',
                'fs_initcall',
                'fs_initcall_sync',
                'rootfs_initcall',
                'device_initcall',
                'device_initcall_sync',
                'late_initcall',
                'late_initcall_sync',
                '__initcall',
                '__exitcall',
                'console_initcall',
                'security_initcall'],
    # keywords in remove_keywords will be removed from each line in tmp file.
    'remove_keywords' : ['__init', '__exit']
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
        self.caller = set()
        self.callee = set()
        self.args = []
        self.code = ''

    def __str__(self):
        '''
        Print Function Object
        '''
        return f'Function: {self.name}\n' +f'Args:{[x for x in self.args]}\n' + f'caller: {self.caller}\n' + f'callee: {self.callee}\n' + f'code: {self.code}\n'

class StaticCodeAnalyizerConfig:
    '''
    StaticCodeAnalyizerConfig class
    '''
    def __init__(self, /, project, dirs, files, build_options, include_paths, ignore_func_list, ignore_lines, remove_keywords):
        '''
        Initialize StaticCodeAnalyizerConfig
        '''
        self.project = project
        self.dirs = set(dirs)
        self.files = set(files)
        self.build_options = build_options
        self.include_paths = include_paths
        self.ignore_func_list = ignore_func_list
        self.ignore_lines = ignore_lines
        self.remove_keywords = remove_keywords

    def __str__(self):
        '''
        Print StaticCodeAnalyizerConfig Object
        '''
        return f'dirs: {self.dirs}\n' + f'files: {self.files}\n' +\
            f'build_options: {self.build_options}\n' + f'include_paths: {self.include_paths}\n' +\
            f'ignore_func_list: {self.ignore_func_list}\n' + f'ignore_lines: {self.ignore_lines}\n' +\
            f'remove_keywords: {self.remove_keywords}\n'

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

    TMP_POST_FIX = '.tmp.c'
    def __to_tmp_file(self, f):
        '''
        Convert file name to tmp file name
        '''
        return f'{f}'+self.TMP_POST_FIX

    def __to_orig_file(self, f):
        '''
        Revert tmp file name to original file name
        '''
        return f[:-(len(self.TMP_POST_FIX))]

    def __get_files_in_directories(self, input_paths):
        '''
        Traverse all files in directories
        '''
        input_paths.add('')
        return set([os.path.join(dirpath, filename) 
                for path in input_paths if path != ''
                    for dirpath, *dirnames, filenames in os.walk(path) 
                        for filename in filenames])

    def __print_diagnostics(self, translation_unit):
        '''
        Print build error messages.
        User must fix all Error / Fatal to get correct result
        '''
        for diag in translation_unit.diagnostics:
            severity_level_to_string = ('Ignored', 'Note', 'Warning', 'Error', 'Fatal')
            print(f'{severity_level_to_string[diag.severity]}: {diag.spelling}')

            if diag.location.file is not None:
                print(f"Location: {self.__to_orig_file(diag.location.file.name)}:{diag.location.line}:{diag.location.column}")
            else:
                print("Location: N/A")

            if diag.severity >= clang.cindex.Diagnostic.Error:
                return "Error:{diag.severity}"
            else: pass
        else: pass
        return "Pass"

    def __get_function_code_block(self, cursor):
        '''
        Get code block for function
        '''

        if cursor.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            start_location = cursor.extent.start
            end_location = cursor.extent.end

            with open(cursor.location.file.name) as source_file:
                try:
                    source_lines = source_file.readlines()
                except Exception as e:
                    source_lines = None
                source_file.close()
            if source_lines != None:
                start_line = start_location.line - 1
                end_line = end_location.line
                code_block = ''.join(source_lines[start_line:end_line])
                return code_block.strip()
            else:
                return ''
        else: pass

    def __get_callees(self, node, func_name):
        '''
        Get code block for function
        '''

        '''Find all CALL_EXPR until FUNCTION_DECL is found for other function'''
        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL and node.spelling != func_name:
            return
        elif node.kind == clang.cindex.CursorKind.CALL_EXPR and node.spelling not in self.__config.ignore_func_list:
            callee_name = node.spelling

            if func_name not in self.__call_graph:
                self.__call_graph[func_name] = Function(func_name)
            else: pass

            if callee_name not in self.__call_graph:
                self.__call_graph[callee_name] = Function(callee_name)
            else: pass

            caller_func = self.__call_graph[func_name]
            callee_func = self.__call_graph[callee_name]

            caller_func.callee.add(callee_name)
            callee_func.caller.add(func_name)
        else: pass
        for child in node.get_children():
            self.__get_callees(child, func_name)
        else: pass

    def __get_functions(self, node):
        '''
        Traverse functions in code
        '''

        '''Found function declaration'''
        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            '''
            We are interested in functions which are
            1) not in the ignore_func_list and
            2) function is defined in given source file or source dir.
            '''
            if node.spelling not in self.__config.ignore_func_list and node.location.file.name in [self.__to_tmp_file(f) for f in self.__file_name]:
                func_name = node.spelling
                '''Get function code block'''
                code_block = self.__get_function_code_block(node)
                if code_block != '':
                    if func_name not in self.__call_graph:
                        func = Function(func_name)
                        for param in node.get_arguments():
                            func.args.append((param.type.spelling, param.displayname))
                        func.code = code_block
                        self.__call_graph[func_name] = func
                    else: pass
                else: pass


                '''Find callees of this function.'''
                self.__get_callees(node, func_name)
            else: pass

        else: pass

        '''Find next FUNCTION_DECL'''
        for child in node.get_children():
            self.__get_functions(child)
        else: pass

    def run(self):
        '''
        Run StaticCodeAnalyizer
        '''
        index = clang.cindex.Index.create()

        '''For all files given by user via dirs and files'''
        for f in self.__file_name:
            '''Create tmp file for parsing'''
            write_file = open(self.__to_tmp_file(f),'w')
            with open(f) as source_file:
                source_lines = source_file.readlines()
                for line in source_lines:
                    for ignore in self.__config.ignore_lines:
                        if ignore in line:
                            break
                        else: pass
                    else:
                        for k in self.__config.remove_keywords:
                            line = line.replace(k, ' ')
                        else: pass
                        write_file.writelines(line)
                else: pass
                source_file.close()
            write_file.close()

            '''Perform parsing on tmp file'''
            print('*'*100)
            translation_unit = index.parse(self.__to_tmp_file(f),
                                           args=[x for x in self.__config.build_options + [''] if x != ''] +
                                                [f'-I{x}' for x in self.__config.include_paths + [''] if x != ''])

            if not translation_unit:
                print("Fetal Error: Failed to parse the source file {}." % (f))
                os.remove(self.__to_tmp_file(f))
                exit(-1)
            else: pass

            '''Check error'''
            if self.__print_diagnostics(translation_unit) != "Pass":
                print("Fetal Error: Failed to parse the source file {}." % (f))
                os.remove(self.__to_tmp_file(f))
                print('*'*100)
                exit(-1)
            else: pass

            '''Traverse Abstract Syntax Tree(AST)'''
            root_cursor = translation_unit.cursor
            self.__get_functions(root_cursor)
            os.remove(self.__to_tmp_file(f))
            print(f'Completed {self.__to_orig_file(root_cursor.spelling)}')
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
            dot.node(f.name, f'{f.name}{tuple([arg[0]+" "+arg[1] for arg in f.args]) if len(f.args) else "void"}')
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
