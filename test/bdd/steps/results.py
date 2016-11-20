""" Steps that check results.
"""

from nose.tools import * # for assert functions

def compare(operator, op1, op2):
    if operator == 'less than':
        return op1 < op2
    elif operator == 'more than':
        return op1 > op2
    elif operator == 'exactly':
        return op1 == op2
    elif operator == 'at least':
        return op1 >= op2
    elif operator == 'at most':
        return op1 <= op2
    else:
        raise Exception("unknown operator '%s'" % operator)

@step(u'(?P<operator>less than|more than|exactly|at least|at most) (?P<number>\d+) results? (?:is|are) returned')
def validate_result_number(context, operator, number):
    numres = len(context.response.result)
    ok_(compare(operator, numres, int(number)),
        "Bad number of results: expected %s %s, got %d." % (operator, number, numres))


@then(u'results contain')
def step_impl(context):
    context.execute_steps("then at least 1 result is returned")

    for line in context.table:
        context.response.match_row(line)

