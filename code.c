int add(int a, int b)
{
	return a+b;
}

int sub(int a, int b)
{
	return a-b;
}

void add_sub()
{
	int a;
	int b;

	sub(add(a, b), b);
}
