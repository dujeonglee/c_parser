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

ignore_func_list = ('likely', 'unlikely', 'WARN', 'WARN_ON', 'BUG', 'BUG_ON')
'''
Compile options ending with ''.
-DMODULE is required for kernel module build.
'''
BUILD_OPTIONS = ('-E', '-fsyntax-only', '-DMODULE')

'''
Include paths ending with ''.
'''
INCLUDE_PATH = (
    '/path/to/include',
    '')

## We need to remove linux kernel specific macro and directives
IGNORE_LINES = ('EXPORT_SYMBOL',
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
                'security_initcall')

REMOVE_KEYWORDS = ('__init', '__exit')

ARGUMENT = [*(x for x in BUILD_OPTIONS if x != '')] + [*(f'-I{x}' for x in INCLUDE_PATH if x != '')]
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

class StaticCodeAnalyizer:
    '''Static code analyzer for clang.'''

    def __init__(self, /, dirName = None, fileName = None):
        '''Initialize StaticCodeAnalyizer'''

        self.callgraph = {}
        self.dirName = None
        self.fileName = []
        self.source_lines = None
        self.file_name = None

        '''
        find all src files in given dir
        '''
        if dirName:
            self.dirName = dirName
            if self.dirName:
                self.fileName = [x for x in self.__enumerate_files_in_directory() if x[-1] == 'c']
            else:
                pass
        else:
            pass
        '''
        Append individual files to fileName list if have any
        '''
        if fileName:
            self.fileName.append(fileName)
        print(f'%d files are loaded' % (len(self.fileName)))
        print(*self.fileName, sep="\n")
        print()

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

    def __enumerate_files_in_directory(self):
        '''Traverse all files in directory'''

        for root, dirs, files in os.walk(self.dirName):
            for file in files:
                file_path = os.path.join(root, file)
                yield file_path
            else:
                pass
        else:
            pass

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
        elif node.kind == clang.cindex.CursorKind.CALL_EXPR and node.spelling not in ignore_func_list:
            callee_name = node.spelling

            if caller_name not in self.callgraph:
                self.callgraph[caller_name] = Function(caller_name)
            else:
                pass # end of "if caller_name != None and caller_name not in self.callgraph"

            if callee_name not in self.callgraph:
                self.callgraph[callee_name] = Function(callee_name)
            else:
                pass #end of "if callee_name != None and callee_name not in self.callgraph"

            caller_func = self.callgraph[caller_name]
            callee_func = self.callgraph[callee_name]
            
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
            if node.spelling not in ignore_func_list and node.location.file.name in [f'{x}.tmp.c' for x in self.fileName]:
                func_name = node.spelling
                '''
                Get function code block
                '''
                code_block = self.__get_function_code_block(node)
                if code_block:
                    if func_name not in self.callgraph:
                        self.callgraph[func_name] = Function(func_name)
                    else:
                        pass # end of "if func_name not in self.callgraph"
                    func = self.callgraph[func_name]
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
        print(ARGUMENT)
        for f in self.fileName:
            write_file = open(f'{f}.tmp.c','w')
            with open(f) as source_file:
                source_lines = source_file.readlines()
                for line in source_lines:
                    for ignore in IGNORE_LINES:
                        if ignore in line:
                            break
                        else:
                            pass
                    else:
                        for k in REMOVE_KEYWORDS:
                            line = line.replace(k, ' ')
                        write_file.writelines(line)
                else:
                    pass
                source_file.close()
            write_file.close()
        else:
            pass

        for f in self.fileName:
            index = clang.cindex.Index.create()
            translation_unit = index.parse(f'{f}.tmp.c', args=ARGUMENT)

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
        
        for f in self.fileName:
            os.remove(f'{f}.tmp.c')
        else:
            pass

    def show(self):
        for x in self.callgraph.values():
            print(x)
        else:
            pass # end of "for x in self.callgraph"

def main():
    # Replace with the path to your C/C++ source file
    #sca = StaticCodeAnalyizer(dirName="C:/Users/sugar/Documents/function_parser/core")
    sca = StaticCodeAnalyizer(fileName="C:/Users/sugar/Documents/function_parser/code.c")
    sca.run()
    sca.show()

if __name__ == "__main__":
    main()
