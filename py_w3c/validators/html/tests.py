#!/usr/bin/python
import unittest
import time
import tempfile

from validator import HTMLValidator
from py_w3c.exceptions import ValidationFault


class TestValidator(unittest.TestCase):
    def setUp(self):
        self.validator = HTMLValidator()

        self.temp_file = tempfile.NamedTemporaryFile()
        self.temp_file.write("""<!DOCTYPE html>
            <html>
            <head bad-attr="i'm bad">
                <title>py_w3c test</title>
            </head>
                <body>
                    <h1>Hello py_w3c</h1>
                </body>
            </html>
        """)
        self.temp_file.file.seek(0)
        time.sleep(1)

    def test_url_validation(self):
        self.validator.validate('http://datetostr.org') # I know exactly there is no errors
        self.assertEqual(self.validator.errors, [])
        self.assertEqual(self.validator.warnings, [])

    def test_validation_by_file_name(self):
        self.validator.validate_file(self.temp_file.file)
        self.assertEqual(len(self.validator.errors), 1)
        self.assertEqual(int(self.validator.errors[0].get("line")), 3)

    def test_validation_by_file_content(self):
        self.validator.validate_file(self.temp_file.name)
        self.assertEqual(len(self.validator.errors), 1)
        self.assertEqual(int(self.validator.errors[0].get("line")), 3)

    def test_fragment_validation(self):
        fragment = u'''<!DOCTYPE html>
            <html>
                <head>
                    <title>testing py_w3c</title>
                </head>
                <body>
                    <badtag>i'm bad</badtag>
                    <div>my div</div>
                </body>
            </html>
        '''.encode("utf-8")
        self.validator.validate_fragment(fragment)
        self.assertEqual(len(self.validator.errors), 1)
        self.assertEqual(int(self.validator.errors[0].get("line"),), 7)

    def test_passing_doctype_forces_validator_to_use_passed_doctype(self):
        doctype = "XHTML 1.0 Strict"
        val = HTMLValidator(doctype=doctype)
        val.validate('http://datetostr.org') # I know exactly there is no errors
        self.assertTrue(doctype in val.result.doctype)

    def test_passing_charset_forces_validator_to_use_passed_charset(self):
        val = HTMLValidator(charset="windows-1251")
        val.validate('http://datetostr.org')
        self.assertEqual(val.result.charset, "windows-1251")

    def test_passing_wrong_charset_raises_ValidationFault_exception(self):
        val = HTMLValidator(charset="win-1251")
        self.assertRaises(ValidationFault, val.validate, 'http://datetostr.org')

if __name__ == '__main__':
    unittest.main()
