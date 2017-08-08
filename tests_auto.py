MARKS = ['FORECASTDEV', 'FORECASTPERCENT', 'KDPERCENT', 'CURYPREDYDIVFACT', 'FPFDEV', 'FPFPERCENT', 'CURPPREDPDEVFACT']
test_file = open('test_INDO01.txt', 'r')
tests_array = []
correct_tests_array = []
for line in test_file:
    tests_array.append(line)

test_file.close()
for i in tests_array:
    test_text_mdx = i.split(':')
    n = test_text_mdx[1].find('(', 0, len(test_text_mdx[1]))
    dim_names = test_text_mdx[1][n:len(test_text_mdx[1]):1]

    dims = []
    dims_with_formal_names = []
    while dim_names.rfind(']', 0, len(dim_names)) != -1:
        beginning = dim_names.find('[', 0, len(dim_names))
        end = dim_names.find(']', 0, len(dim_names))
        new_dim = dim_names[beginning:end + 1:1]
        dim_names = dim_names[end + 2:len(dim_names):1]
        dims.append(new_dim)
        dim_digits = new_dim[1:3:1]
        if dim_digits == '09':
            dims_with_formal_names.append('[BGLEVELS].' + new_dim)
        if dim_digits == '08':
            dims_with_formal_names.append('[TERRITORIES].' + new_dim)
        if dim_digits == '05':
            dims_with_formal_names.append('[KDGROUPS].' + new_dim)
        if dim_digits == '03':
            dims_with_formal_names.append('[MARKS].' + new_dim)
        if dim_digits in MARKS:
            dims_with_formal_names.append('[MARKS].' + new_dim)
        if dim_digits == '14':
            dims_with_formal_names.append('[RZPR].' + new_dim)
        if dim_digits == '25':
            dims_with_formal_names.append('[BIFB].' + new_dim)

        updated_dims = ''
    for j in dims_with_formal_names:
        updated_dims = updated_dims + j + ', '

    updated_dims = updated_dims[0:len(updated_dims) - 2:1]
    test_text_mdx[1] = test_text_mdx[1][0:n:1] + '(' + updated_dims + ')'
    new_test = test_text_mdx[0] + ':' + test_text_mdx[1]
    correct_tests_array.append(new_test)

f = test_file = open('test_INDO01.txt', 'w')
for test in correct_tests_array:
    f.write(test + '\n')
