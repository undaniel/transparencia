import unittest

from descarga import datos_formulario

HTML = """
<form id="OTRO:formInfo" action="/ficha?a=1&amp;b=2" method="post">
  <input type="hidden" name="javax.faces.ViewState" value="VS-123" />
  <input type="hidden" name="javax.faces.encodedURL" value="/enc?x=1&amp;y=2" />
  <button name="OTRO:formInfo:j_idt99" alt="Descargar CSV">Descargar CSV</button>
</form>
"""


class FormularioTest(unittest.TestCase):
    def test_descubre_id_y_campos(self):
        form_id, action, vs, enc, boton = datos_formulario(HTML)
        self.assertEqual(form_id, "OTRO:formInfo")
        self.assertEqual(action, "/ficha?a=1&b=2")
        self.assertEqual(vs, "VS-123")
        self.assertEqual(enc, "/enc?x=1&y=2")
        self.assertEqual(boton, "OTRO:formInfo:j_idt99")


if __name__ == "__main__":
    unittest.main()
