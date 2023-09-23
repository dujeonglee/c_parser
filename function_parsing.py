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

import os
import clang.cindex

config = {
    'dirs' : ['sample'],
    'files' : [],
    'build_options' : ['-E', '-fsyntax-only', '-DMODULE'],
    'include_paths' : ['sample'],
    'ignore_func_list' : ['likely', 'unlikely', 'WARN', 'WARN_ON', 'BUG', 'BUG_ON'],
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
    'remove_keywords' : ['__init', '__exit']
}

class Function:
    '''Function class'''

    def __init__(self, name):
        '''Initialize Function'''

        self.name = name
        self.caller = set()
        self.callee = set()
        self.code = ""
    def __str__(self):
        '''Print Function Object'''
        return f'Function: {self.name}\n' + f'caller: {self.caller}\n' + f'callee: {self.callee}\n' + f'code: {self.code}\n'

class StaticCodeAnalyizerConfig:
    def __init__(self, /, dirs, files, build_options, include_paths, ignore_func_list, ignore_lines, remove_keywords):
        self.dirs = dirs
        self.files = files
        self.build_options = build_options
        self.include_paths = include_paths
        self.ignore_func_list = ignore_func_list
        self.ignore_lines = ignore_lines
        self.remove_keywords = remove_keywords
    def __str__(self):
        '''Print Function Object'''
        return f'dirs: {self.dirs}\n' + f'files: {self.files}\n' +\
            f'build_options: {self.build_options}\n' + f'include_paths: {self.include_paths}\n' +\
            f'ignore_func_list: {self.ignore_func_list}\n' + f'ignore_lines: {self.ignore_lines}\n' +\
            f'remove_keywords: {self.remove_keywords}\n'

class StaticCodeAnalyizer:
    '''Static code analyzer for clang.'''

    def __init__(self, /, config):
        '''Initialize StaticCodeAnalyizer'''

        self.__call_graph = {}
        self.__file_name = []
        self.__config = config

        '''
        find all src files in given dir
        '''
        self.__file_name = self.__get_files_in_directories(self.__config.dirs) + self.__config.files

        '''
        Append individual files to fileName list if have any
        '''
        print(f'%d files are loaded' % (len(self.__file_name)))
        print(*self.__file_name, sep="\n")
        print()
        print(self.__config)
        print()

    def __get_files_in_directories(self, input_paths):
        '''Traverse all files in directories'''
        input_paths.append('')
        return [os.path.join(dirpath, filename) 
                for path in input_paths if path != ''
                    for dirpath, *dirnames, filenames in os.walk(path) 
                        for filename in filenames]

    def __print_diagnostics(self, translation_unit):
        '''print build error messages. user must fix the errors to get correct result'''

        for diag in translation_unit.diagnostics:
            print(f"Severity: {diag.severity}")
            
            if diag.location.file is not None:
                print(f"Location: {diag.location.file.name}:{diag.location.line}:{diag.location.column}")
            else:
                print("Location: N/A")
            
            print(f"Spelling: {diag.spelling}")
            print()


    def __get_function_code_block(self, cursor):
        '''Get code block for function'''

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
                return ""

    def __get_callees(self, node, caller_name):
        '''Get code block for function'''

        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL and node.spelling != caller_name:
            return
        elif node.kind == clang.cindex.CursorKind.CALL_EXPR and node.spelling not in self.__config.ignore_func_list:
            callee_name = node.spelling

            if caller_name not in self.__call_graph:
                self.__call_graph[caller_name] = Function(caller_name)
            else:
                pass # end of "if caller_name != None and caller_name not in self.__call_graph"

            if callee_name not in self.__call_graph:
                self.__call_graph[callee_name] = Function(callee_name)
            else:
                pass #end of "if callee_name != None and callee_name not in self.__call_graph"

            caller_func = self.__call_graph[caller_name]
            callee_func = self.__call_graph[callee_name]
            
            caller_func.callee.add(callee_name)
            callee_func.caller.add(caller_name)
        else:
            pass
        for child in node.get_children():
            self.__get_callees(child, caller_name)

    def __get_functions(self, node):
        '''Traverse code'''

        '''
        Found function declaration.
        '''
        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
            '''
            We are interested in functions which are
            1) not in the ignore_func_list and
            2) function is defined in given source file or source dir.
            '''
            if node.spelling not in self.__config.ignore_func_list and node.location.file.name in [f'{x}.tmp.c' for x in self.__file_name]:
                func_name = node.spelling
                '''
                Get function code block
                '''
                code_block = self.__get_function_code_block(node)
                if code_block:
                    if func_name not in self.__call_graph:
                        self.__call_graph[func_name] = Function(func_name)
                    else:
                        pass # end of "if func_name not in self.__call_graph"
                    func = self.__call_graph[func_name]
                    if func_name in code_block:
                        func.code = code_block if len(code_block) > len(func.code) else func.code
                    else:
                        pass
                else:
                    pass # end of "if code_block:"
                '''
                Find callees of this function.
                '''
                self.__get_callees(node, func_name)
            else:
                pass
        else:
            pass # end of "node.kind == clang.cindex.CursorKind.FUNCTION_DECL"

        '''
        Find next function declaration.
        '''
        for child in node.get_children():
            self.__get_functions(child)
        else:
            pass # end of "for child in node.get_children()"

    def run(self):
        for f in self.__file_name:
            write_file = open(f'{f}.tmp.c','w')
            with open(f) as source_file:
                source_lines = source_file.readlines()
                for line in source_lines:
                    for ignore in self.__config.ignore_lines:
                        if ignore in line:
                            break
                        else:
                            pass
                    else:
                        for k in self.__config.remove_keywords:
                            line = line.replace(k, ' ')
                        write_file.writelines(line)
                else:
                    pass
                source_file.close()
            write_file.close()
        else:
            pass

        for f in self.__file_name:
            index = clang.cindex.Index.create()
            translation_unit = index.parse(f'{f}.tmp.c',
                                           args=[x for x in self.__config.build_options + [''] if x != ''] +
                                                [f'-I{x}' for x in self.__config.include_paths + [''] if x != ''])

            if not translation_unit:
                print("Fetal Error: Failed to parse the source file {}." % (f))
                exit()
            self.__print_diagnostics(translation_unit)
            root_cursor = translation_unit.cursor
            print(root_cursor.spelling)

            self.__get_functions(root_cursor)
            del translation_unit
            del index
        else:
            pass
        
        for f in self.__file_name:
            os.remove(f'{f}.tmp.c')
        else:
            pass

    def show(self):
        for x in self.__call_graph.values():
            print(x)
        else:
            pass # end of "for x in self.__call_graph"

def main():
    # Replace with the path to your C/C++ source file
    sca = StaticCodeAnalyizer(StaticCodeAnalyizerConfig(**config))
    sca.run()
    sca.show()

if __name__ == "__main__":
    main()
