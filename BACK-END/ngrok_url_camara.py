from pyngrok import ngrok

class ngrokurl:
    # Método para obtener la URL pública de ngrok
    def __init__(self, puerto):
        # Abre un túnel en el puerto indicado y guarda la URL pública en la variable
        conexion = ngrok.connect(puerto)
        self.url_publica = conexion.public_url
