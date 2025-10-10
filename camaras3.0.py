import sqlite3
import cv2
def acceder():
# Conectar a la base de datos local
    try:
        conn = sqlite3.connect("/home/nico/Documents/Tarea 7 Ciber/usuarios.db")
        cursor = conn.cursor()
# Seleccionar usuario y su cámara
        camaras = input("Ingrese el número de cámaras a usar:\n")
        caps = [] #arreglo de streams de video
        nombres = [] #arreglo de nombres de usuarios
        for i in range(int(camaras)):

            value = input("Ingrese el número de usuario a usar la cámara:\n")
            cursor.execute(f"SELECT nombre, ip_camara FROM usuarios WHERE id_usuario = {value};")
            usuario = cursor.fetchone()
            if usuario:
                nombre, ip_camara = usuario
                nombres.append(nombre) #se añaden usuarios al arreglo
                print(f"Conectando a la cámara de {nombre} en {ip_camara}...")
            # Abrir stream de video
                cap = cv2.VideoCapture(ip_camara)
                caps.append(cap) #se añaden caps al arreglo
        #bucle para presentar video
        window_width = 320 #Ancho de ventana cambiado
        window_height = 240 #Altura de ventana cambiada
        while True:
            for i, cap in enumerate(caps): #bucle de streams de video
                ret, frame = cap.read()
                if not ret:
                    print(f"Error al obtener video de la cámara {nombres[i]}")
                    break
                cv2.namedWindow(f"Camara de {nombres[i]}", cv2.WINDOW_NORMAL) #"unfortunately you can't manually resize a nameWindow window without Qt backend." -De stackexchange
                frame = cv2.resize(frame, (window_width, window_height)) #Para definir largo y ancho del stream predeterminado
                cv2.imshow(f"Camara de {nombres[i]}", frame)
            if cv2.waitKey(1) == 27: # tecla ESC para salir
                break
        #eliminación de ventanas
        for cap in caps:
            cap.release()
            cv2.destroyAllWindows()
        else:
            print("Usuario no encontrado")
    #manejo de errores, lo cual deje bastante de lado a pesar de ser una implementación relativamente sencilla
    except Exception as e:
        print(f"Ocurrió un error: {e}")
#parte de la antigua implementación, antes era como FNAF, salías de una cámara y podías acceder a otra
#camaras = input("Ingrese el número de cámaras a usar:\n")
#for i in range(int(camaras)):
acceder()
