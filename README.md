# c_parser
![sample output](https://github.com/dujeonglee/c_parser/blob/main/sample_project.png?raw=true)


## Requirement
### libclang
#### Install python libaray
$ pip install libclang
- If env is not setup properly, one need to specify libclang.so(linux) libclang.dll(windows) using
clang.cindex.Config.set_library_path('/path/to/libclang') in StaticCodeAnalyizer.py
- Site: https://pypi.org/project/libclang/
### graphviz
#### Install python libaray
$ pip install graphviz
- Site: https://graphviz.org/download/

## How to use
```
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
```
