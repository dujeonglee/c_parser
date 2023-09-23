#include "func.h"
#include <stdio.h>

void func_a(void)
{
    printf("%s %u", __FILE__, __LINE__);
    func_b();
    func_c();
}
void func_b(void)
{
    printf("%s %u", __FILE__, __LINE__);
    func_c();
}
void func_c(void)
{
    printf("%s %u", __FILE__, __LINE__);
}

void func_d(void)
{
    printf("%s %u", __FILE__, __LINE__);
}