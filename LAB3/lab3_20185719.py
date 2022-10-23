import yaml
import requests

class Alumno:
    def __init__(self,nombre,codigo,pc):
        self.nombre = nombre
        self.codigo = codigo
        self.pc = pc
     
class Curso:
    def __init__(self,nombre,estado, codigo):
        self.nombre = nombre
        self.estado = estado
        self.codigo = codigo
        self.alumnos = []
        self.servidores = []
        self.serviciosPermitidos = []
        
    def agregarAlumnos(self, Alumno):
        self.alumnos.append(Alumno)
        

    def borrarAlumnos(self,Alumno):
        self.alumnos.remove(Alumno)
    
    def anadirServidor(self,Servidor):
        self.servidores.append(Servidor)

class Servicio:
    def __init__(self,nombre,protocolo,puerto):
        self.nombre = nombre
        self.protocolo = protocolo
        self.puerto = puerto

class Servidor:
    def __init__(self,nombre,direccionIP,servicios,mac):
        self.nombre = nombre
        self.direccionIP = direccionIP
        self.mac = mac
        self.servicios = servicios

class Conexion:
    def __init__(self,handler,alumno,servidor,servicio):
        self.handler = handler
        self.alumno = alumno
        self.servidor = servidor
        self.servicio = servicio
        self.flows = []
    
    def agregarFlows(self,flow):
        self.flows.append(flow)
    
def get_attachement_points(mac):
    datos = requests.get("http://10.20.12.126:8080/wm/device/").json()
    for i in datos:
        if mac == i["mac"][0]:
            dpid = i["attachmentPoint"][0]["switchDPID"]
            puerto = i["attachmentPoint"][0]["port"]
    return dpid,puerto

class StaticEntryPusher:
 
    def __init__(self, server):
        self.server = 'http://'+server+':8080'
 
    def put(self, data):
        path = self.server+'/wm/staticflowpusher/json'
        resp=requests.post(path, json=data)
    
    def delete(self,data):
        path = self.server+'/wm/staticflowpusher/json'
        resp=requests.delete(path, json=data)

def get_route(dpid_origen, puerto_origen, dpid_destino, puerto_destino):
    datos = requests.get("http://10.20.12.126:8080/wm/topology/route/"+str(dpid_origen)+"/"+
            str(puerto_origen)+"/"+str(dpid_destino)+"/"+str(puerto_destino)+"/json").json()
    listaRutas = []
    for i in datos:
        listaRutas.append([i["switch"],i["port"]["portNumber"]])
    return listaRutas

def build_route(ruta,alumno,servicio,servidor):
    listaFlows=[]
    pusher = StaticEntryPusher("10.20.12.126")
    ip_proto=""
    if(str(servicio.protocolo).lower() == "tcp"):
        ip_proto = "0x06"
    elif(str(servicio.protocolo).lower() == "udp"):
        ip_proto = "0x11"
    elif(str(servicio.protocolo).lower() == "sctp"):
        ip_proto = "0x84"
    elif(str(servicio.protocolo).lower() == "icmpv4"):
        ip_proto = "0x01"

    if(ip_proto != ""):
        for i in range(len(ruta)):
            if(i%2==0):
                flow = {
                    "switch":ruta[i][0],
                    "name" : "flow "+str(i)+": servicio ->"+servicio.nombre+", alumno ->" +alumno.nombre+", servidor ->"+servidor.nombre,
                    "cookie":"0",
                    "eth_type":"0x0800",
                    "ip_proto":ip_proto,
                    "eth_src": alumno.pc,
                    "eth_dst": servidor.mac,
                    "ipv4_dst": servidor.direccionIP,
                    "tp_dst": servicio.puerto,
                    "active": "true",
                    "actions" : "output="+str(ruta[i+1][1]) 
                }

                flowARP = { 
                    "switch":ruta[i][0],
                    "name" : "flowARP "+str(i)+": servicio ->"+servicio.nombre+", alumno ->" +alumno.nombre+", servidor ->"+servidor.nombre,
                    "cookie":"0",
                    "eth_type":"0x0806", 
                    "arp_opcode":"1", 
                    "eth_src": alumno.pc,
                    "active" : "true",
                    "actions" : "output="+str(ruta[i+1][1]) 
                }
                
                listaFlows.append(flow)
                listaFlows.append(flowARP)
            
            else:

                flowRegreso = {
                    "switch":ruta[i][0],
                    "name" : "flowRegreso"+str(i)+": servicio ->"+servicio.nombre+", alumno ->" +alumno.nombre+", servidor ->"+servidor.nombre,
                    "cookie":"0",
                    "eth_type":"0x0800",
                    "ip_proto":ip_proto,
                    "eth_dst": alumno.pc,
                    "eth_src": servidor.mac,
                    "ipv4_src": servidor.direccionIP,
                    "tp_src": servicio.puerto,
                    "active": "true",
                    "actions" : "output="+str(ruta[i-1][1]) 
                }

                flowARPRegreso = { 
                    "switch":ruta[i][0],
                    "name" : "flowARPRegreso"+str(i)+": servicio ->"+servicio.nombre+", alumno ->" +alumno.nombre+", servidor ->"+servidor.nombre,
                    "cookie":"0",
                    "eth_type":"0x0806", 
                    "arp_opcode":"2", 
                    "eth_src": servidor.mac,
                    "active" : "true",
                    "actions" : "output="+str(ruta[i-1][1]) 
                }

                listaFlows.append(flowRegreso)
                listaFlows.append(flowARPRegreso)

        for i in listaFlows:
            pusher.put(i)
    else:
        print("No se ha implementado el protocolo")

    return listaFlows

def mostrar_menu(opciones):
    print('\n###########################################################')
    print('Network Policy manager de la UPSM')
    print('###########################################################\n')
    print('Seleccione una opción:')
    for clave in sorted(opciones):
        print(f' {clave}) {opciones[clave][0]}')

def leer_opcion(opciones):
    while (opcion := input('>>>')) not in opciones:
        print('Opción incorrecta, vuelva a intentarlo.')
    return opcion

def ejecutar_opcion(opcion, opciones):
    opciones[opcion][1]()

def generar_menu(opciones, opcion_salida):
    opcion = None
    while opcion != opcion_salida:
        mostrar_menu(opciones)
        opcion = leer_opcion(opciones)
        ejecutar_opcion(opcion, opciones)
        print()

def menu_principal():
    opciones = {
        '1': ('Importar', importar),
        '2': ('Exportar', exportar),
        '3': ('Cursos', cursos),
        '4': ('Alumnos', alumnos),
        '5': ('Servidores', servidores),
        '6': ('Políticas', políticas),
        '7': ('Conexiones', conexiones),
        '8': ('Salir', salir)
    }

    generar_menu(opciones, '8')


def importar():
    global listaCursos
    global listaAlumnos
    global listaServidores
    global listaServicios
    global listaConexiones 
    listaConexiones = []

    with open("data.yaml","r") as stream:
        try:
            datos = yaml.safe_load(stream)
            listaCursos = []
            listaAlumnos = []
            listaServidores = []
            listaServicios = []
            for i in datos["cursos"]:
                curso = Curso(i["nombre"], i["estado"], i["codigo"])
                for j in i["alumnos"]:
                    curso.agregarAlumnos(j)
                for k in i["servidores"]:
                    serviciosPermitidos = []
                    for m in k["servicios_permitidos"]:
                        serviciosPermitidos.append(m)
                    curso.anadirServidor(Servidor(k["nombre"],"",serviciosPermitidos,""))
                listaCursos.append(curso)
            for i in datos["alumnos"]:
                alumno = Alumno(i["nombre"], i["codigo"],i["mac"])
                listaAlumnos.append(alumno)
            for i in datos["servidores"]:
                listaServicios =  []
                for j in i["servicios"]:
                    servicio = Servicio(j["nombre"],j["protocolo"],j["puerto"])
                    listaServicios.append(servicio)
                servidor = Servidor(i["nombre"], i["ip"],listaServicios,i["mac"])    
                listaServidores.append(servidor)
            print("Se realizó el importe del archivo con éxito")
        except yaml.YAMLError as exc:
            print("El archivo se encuentra dañado ")


def exportar():
    print('Esta opción no ha sido implementada')


def cursos():

    try:

        def listarCursos():
            print("-------------- Lista de Cursos ----------------")
            for n in listaCursos:
                print("Nombre: " + str(n.nombre))
                print("Estado: " + str(n.estado))
                print("Alumnos inscritos: ")
                for j in n.alumnos:
                    print("- " + str(j))
                print("Servidores: ")
                for k in n.servidores:
                    print("- " +  str(k.nombre))
                    print("Servicios permitidos: ")
                    for m in k.servicios:
                        print("- " + str(m))

        def mostrarDetalleCursos():
            cursoBuscar = input("Ingrese el nombre o código del curso para mayor información: ")
            noExiste = True
            for i in listaCursos:
                if(cursoBuscar.lower() == str(i.nombre).lower() or cursoBuscar.lower() == str(i.codigo).lower()):
                    print("Nombre: " + str(i.nombre))
                    print("Estado: " + str(i.estado))
                    print("Alumnos inscritos: ")
                    for j in i.alumnos:
                        print("- " + str(j))
                    print("Servidores: ")
                    for k in i.servidores:
                        print("- " +  str(k.nombre))
                        print("Servicios permitidos: ")
                        for m in k.servicios:
                            print("- " + str(m))
                    noExiste = False
                    break
            if noExiste:
                print("No se han encontrado resultados para su búsqueda")

        def actualizarCursos():

            def agregarAlumno():
                alumnoCodigo = input("Ingrese el código del alumno que desea agregar: ")
                noAlumno = True
                for i in listaAlumnos:
                    if(alumnoCodigo == str(i.codigo)):
                        cursoBuscar.agregarAlumnos(alumnoCodigo)
                        listaCursos[pos] = cursoBuscar
                        noAlumno = False
                        print("El alumno se agregó exitosamente")
                        break
                if noAlumno:
                    print("El alumno no existe")

            def eliminarAlumno():
                alumnoBuscar = input("Ingrese el código del alumno que desea eliminar: ")
                noExiste = True
                for i in cursoBuscar.alumnos:
                    if(alumnoBuscar == str(i)):
                        cursoBuscar.borrarAlumnos(i)
                        listaCursos[pos] = cursoBuscar
                        noExiste = False
                        print("El alumno se eliminó exitosamente")
                        break
                if noExiste:
                    print("No se han encontrado resultados para su búsqueda")
                        
            def menu_actualizarCurso():
                opciones = {
                    '1': ('Agregar alumno', agregarAlumno),
                    '2': ('Eliminar alumno', eliminarAlumno),
                    '3': ('Salir', salir),
                }

                generar_menu(opciones, '3')
            
            cursoBuscar = input("Ingrese el nombre o código del curso que desea actualizar: ")
            noExiste = True
            pos = 0
            for i in listaCursos:
                if(cursoBuscar.lower() == str(i.nombre).lower() or cursoBuscar == str(i.codigo)):
                    cursoBuscar = i
                    menu_actualizarCurso()
                    noExiste = False
                    break
                pos+=1
            if noExiste:
                print("No se han encontrado resultados para su búsqueda")


        def menu_cursos():
            opciones = {
                '1': ('Listar', listarCursos),
                '2': ('Mostrar detalle', mostrarDetalleCursos),
                '3': ('Actualizar', actualizarCursos),
                '4': ('Salir', salir),
            }

            generar_menu(opciones, '4')
        
        menu_cursos()
    
    except:
        print("Debe importar un archivo")


def alumnos():

    try:

        def agregarAlumnos():
            alumnoNombre = input("Ingrese el nombre del alumno que desea agregar: ")
            alumnoCodigo = input("Ingrese el código del alumno que desea agregar: ")
            alumnoMAC = input("Ingrese la MAC del alumno que desea agregar: ")
            noAlumno = True
            for i in listaAlumnos:
                if(alumnoCodigo == str(i.codigo) and alumnoNombre.lower() == str(i.nombre).lower and alumnoMAC == str(i.mac)):
                    noAlumno = False
                    print("El alumno ya existe")
                    break
            if noAlumno:
                alumnoAgregar = Alumno(alumnoNombre,alumnoCodigo,alumnoMAC)
                listaAlumnos.append(alumnoAgregar)
                print("El alumno se agregó exitosamente")

        def listarAlumnos():
            print("-------------- Lista de Alumnos ----------------")
            for i in listaAlumnos:
                print("Nombre: " + str(i.nombre))
                print("Código: " + str(i.codigo))
                print("MAC: " + str(i.pc))

        def mostrarDetalleAlumnos():
            alumnoBuscar = input("Ingrese el nombre o código del alumno para mayor información: ")
            noExiste = True
            for i in listaAlumnos:
                if(alumnoBuscar.lower() == str(i.nombre).lower() or alumnoBuscar == str(i.codigo)):
                    print("Nombre: " + str(i.nombre))
                    print("Código: " + str(i.codigo))
                    print("MAC: " + str(i.pc))
                    noExiste = False
                    break
            if noExiste:
                print("No se han encontrado resultados para su búsqueda")
    

        def menu_alumnos():
            opciones = {
                '1': ('Listar', listarAlumnos),
                '2': ('Mostrar detalle', mostrarDetalleAlumnos),
                '3': ('Agregar alumno', agregarAlumnos),
                '4': ('Salir', salir),
            }

            generar_menu(opciones, '4')
        
        menu_alumnos()
    
    except:
        print("Debe importar un archivo")


def servidores():

    try:

        def listarServidores():
            print("-------------- Lista de Servidores ----------------")
            for i in listaServidores:
                print("Nombre: " + str(i.nombre))
                print("Dirección IP: " + str(i.direccionIP))
                print("Dirección MAC: " + str(i.mac))
                print("Servicios: ")
                for j in range(len(listaServidores)):
                    if(i.nombre == listaServidores[j].nombre):
                        for k in listaServidores[j].servicios:
                            print("- " + str(k.nombre))
                        break

        def mostrarDetalleServidores():
            servidorBuscar = input("Ingrese el nombre o dirección IP del servidor para mayor información: ")
            noExiste = True
            for i in listaServidores:
                if(servidorBuscar.lower() == str(i.nombre).lower() or servidorBuscar == str(i.direccionIP)):
                    print("Nombre: " + str(i.nombre))
                    print("Dirección IP: " + str(i.direccionIP))
                    print("Dirección MAC: " + str(i.mac))
                    print("Servicios: ")
                    for j in i.servicios:
                        print("Servicio: "+ str(j.nombre))
                        print("Puerto: "+str(j.puerto))
                        print("Protocolo: "+ str(j.protocolo))
                    noExiste = False
                    break
            if noExiste:
                print("No se han encontrado resultados para su búsqueda")

        def menu_servidores():
            opciones = {
                '1': ('Listar', listarServidores),
                '2': ('Mostrar detalle', mostrarDetalleServidores),
                '3': ('Salir', salir),
            }

            generar_menu(opciones, '3')
        
        menu_servidores()
    
    except:
        print("Debe importar un archivo")


def políticas():
    print('Esta opción no ha sido implementada')
    

def conexiones():

    try:
        def alumnoAutorizado(servicio, servidor,alumno):
            activo = False
            for i in listaCursos:
                for j in i.servidores:
                    if(alumno in str(i.alumnos) and str(i.estado).lower()== "dictando" and str(servidor).lower() in str(j.nombre).lower() and str(servicio).lower() in str(j.servicios).lower()):
                        activo = True
                        break 
                else:
                    continue
                break       
            return activo

        def listarConexiones():
            if(len(listaConexiones)!=0):
                print("-------------- Lista de Conexiones ----------------")
                for i in listaConexiones:
                    print("Handler: " + str(i.handler))
                    print("Alumno: " + str(i.alumno.nombre))
                    print("Servidor: " + str(i.servidor.nombre))
                    print("Servicio: " + str(i.servicio.nombre) + "\n\n")
            else:
                print("No existen conexiones")

        def crearConexiones():
            alumno = input("Ingrese el nombre o código del alumno: ")
            servidor = input("Ingrese el nombre o dirección IP del Servidor: ")
            servicio = input("Ingrese el tipo de servicio para la conexion: ")

            servidorExiste = False
            alumnoExiste = False
            servicioExiste = False

            for i in listaAlumnos:
                if(alumno.lower() == str(i.nombre).lower() or alumno == str(i.codigo)):
                    alumno = i
                    alumnoExiste =  True
                    break   

            for i in listaServidores:
                if(servidor.lower() == str(i.nombre).lower() or servidor == str(i.direccionIP)):
                    servidor = i
                    servidorExiste =  True
                    break     
            
            for i in listaServicios:
                if(servicio.lower() == str(i.nombre).lower()):
                    servicio = i
                    servicioExiste =  True
                    break

            if(alumnoExiste and servidorExiste and servicioExiste):
                activo = alumnoAutorizado(servicio.nombre, servidor.nombre,alumno.codigo)
                if(activo):
                    print("El alumno está autorizado")
                    handler = servicio.nombre+"/"+servidor.nombre+"/"+alumno.codigo
                    existeHandler = False
                    for i in listaConexiones:
                        if(handler == str(i.handler)):
                            existeHandler = True
                            break
                    if(existeHandler == False):
                        conexion = Conexion(handler,alumno,servidor,servicio)
                        dpidAlumno, puertoAlumno = get_attachement_points(alumno.pc)
                        dpidServidor, puertoServidor = get_attachement_points(servidor.mac)
                        rutas = get_route(dpidAlumno, puertoAlumno, dpidServidor, puertoServidor) 
                        flows = build_route(rutas,alumno,servicio,servidor)
                        for i in flows:
                            conexion.agregarFlows(i)  
                        listaConexiones.append(conexion)
                        print("La conexión se creó exitosamente")
                    else:
                        print("Esta conexión ya existe")
                else:
                    print("El alumno no está autorizado")
            else:
                print("No existe información con los datos ingresados")

        def borrarConexiones():
            if(len(listaConexiones)!=0):
                handler = input("Ingrese el handler/identificador de la conexión que desea borrar: ")
                pusher = StaticEntryPusher("10.20.12.126")
                for i in listaConexiones:
                    if(i.handler == handler):
                        for j in i.flows:
                            pusher.delete(j)
                        listaConexiones.remove(i)
                        print("La conexión se eliminó exitosamente")
                        break
            else:
                print("No existen conexiones")

        def menu_conexiones():
            opciones = {
                '1': ('Crear', crearConexiones),
                '2': ('Listar', listarConexiones),
                '3': ('Eliminar', borrarConexiones),
                '4': ('Salir', salir),
            }

            generar_menu(opciones, '4')
        
        menu_conexiones()
    except:
        print("Debe importar un archivo")


def salir():
    print('Salir')


if __name__ == '__main__':
    menu_principal()
    