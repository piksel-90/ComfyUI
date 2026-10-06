import unittest

from translator import normalize_american_english, protect_prompt_syntax, restore_prompt_syntax


class TranslatorHelpersTest(unittest.TestCase):
    def test_protect_and_restore(self):
        source = "portret kobiety, <lora:FaceDetail:0.8>, embedding:bad_hands, __camera__"
        masked, protected = protect_prompt_syntax(source)
        self.assertNotIn("<lora:FaceDetail:0.8>", masked)
        self.assertNotIn("embedding:bad_hands", masked)
        self.assertEqual(restore_prompt_syntax(masked, protected), source)

    def test_restore_tolerates_spaces_in_placeholder(self):
        source = "<lora:Foo:1.0>"
        masked, protected = protect_prompt_syntax(source)
        spaced = masked.replace("PRESERVE", " PRESERVE ")
        self.assertEqual(restore_prompt_syntax(spaced, protected), source)

    def test_us_spelling(self):
        self.assertEqual(
            normalize_american_english("grey colour in the centre"),
            "gray color in the center",
        )


if __name__ == "__main__":
    unittest.main()
