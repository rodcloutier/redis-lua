from unittest import TestCase

from redis.exceptions import ResponseError

from redis_lua import parse_script
from redis_lua.exceptions import (
    ScriptNotFoundError,
    CyclicDependencyError,
    ScriptError,
    parse_response_error_message,
    error_handler,
)


class ExceptionsTests(TestCase):

    def test_script_not_found_error(self):
        exception = ScriptNotFoundError(name='foo', filename=r'C:\foo.lua')

        self.assertEqual(
            "No such script 'foo' found at 'C:\\foo.lua'",
            str(exception),
        )

    def test_cyclic_dependency_error_as_string(self):
        exception = CyclicDependencyError(cycle=['a', 'b', 'c'])

        self.assertEqual('a -> b -> c', str(exception))

    def test_script_error_as_string(self):
        cache = {}
        parse_script(
            name='foo',
            content='local a = b;',
            cache=cache,
        )
        script = parse_script(
            name='bar',
            content='%include "foo"',
            cache=cache,
        )
        line = 1
        lua_error = "unknown variable b"
        message = (
            "ERR ResponseError (in f_1234): user_script:1: unknown "
            "variable b"
        )
        exception = ScriptError(
            script=script,
            line=line,
            lua_error=lua_error,
            message=message,
        )

        self.assertEqual(
            """
unknown variable b
LUA Traceback (most recent script last):
  Script "bar", line 1
    %include "foo"
  Script "foo", line 1
    local a = b;
            """.strip().format(
                lua_error=lua_error,
            ),
            str(exception),
        )

    def test_parse_response_error_message(self):
        message = (
            "Error running script (call to f_5b4ae8e72ea3e17bf3d44082ade715c88"
            "f1a81ba): @enable_strict_lua:8: user_script:4: Script attempted t"
            "o create global variable 'c'"
        )
        result = parse_response_error_message(message)

        self.assertEqual(
            {
                'error': (
                    "Error running script (call to f_5b4ae8e72ea3e17bf3d44082a"
                    "de715c88f1a81ba)"
                ),
                'script': 'user_script',
                'line': 4,
                'lua_error': "Script attempted to create global variable 'c'",
            },
            result,
        )

    def test_error_handler(self):
        name = 'foo'
        content = """
local a = 1;
local b = 2;
local c = 3;
local d = 4;
local e = 5;
local f = 6;
local g = 7;
local h = 8;
local i = 9;
local j = 10;
local k = 11;
local l = 12;
"""

        script = parse_script(
            name=name,
            content=content,
        )
        exception = ResponseError(
            "ERR something is wrong: f_1234abc:11: my lua error",
        )

        with self.assertRaises(ScriptError) as error:
            with error_handler(script=script):
                raise exception

        self.assertEqual(
            script,
            error.exception.script,
        )
        self.assertEqual(
            11,
            error.exception.line,
        )
        self.assertEqual(
            'my lua error',
            error.exception.lua_error,
        )
        self.assertEqual(
            'something is wrong',
            error.exception.message,
        )

    def test_error_handler_unknown_message(self):
        name = 'foo'
        content = ""

        script = parse_script(
            name=name,
            content=content,
        )
        exception = ResponseError("ERR Unknown error")

        with self.assertRaises(ResponseError) as error:
            with error_handler(script=script):
                raise exception

        self.assertIs(exception, error.exception)
