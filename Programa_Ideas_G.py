from datetime import datetime
from enum import Enum
import hashlib
import hmac
import os


class EstadoProyecto(Enum):
    REGISTRADO = "REGISTRADO"
    EN_PROCESO = "EN PROCESO"
    TERMINADO = "TERMINADO"


class Actividad:
    def __init__(self, id_actividad, descripcion, fecha_inicio, fecha_fin):
        if fecha_fin < fecha_inicio:
            raise ValueError("La fecha fin no puede ser anterior a la fecha inicio.")
        self.__id_actividad = id_actividad
        self.__descripcion = descripcion
        self.__fecha_inicio = fecha_inicio
        self.__fecha_fin = fecha_fin
        self.__terminada = False

    @property
    def id_actividad(self):
        return self.__id_actividad

    @property
    def descripcion(self):
        return self.__descripcion

    @property
    def fecha_inicio(self):
        return self.__fecha_inicio

    @property
    def fecha_fin(self):
        return self.__fecha_fin

    @property
    def terminada(self):
        return self.__terminada

    def se_cruza_con(self, otra):
        return self.__fecha_inicio <= otra.fecha_fin and otra.fecha_inicio <= self.__fecha_fin

    def marcar_terminada(self):
        self.__terminada = True

    def duracion_dias(self):
        return (self.__fecha_fin - self.__fecha_inicio).days + 1

    def __str__(self):
        estado = "Completada" if self.__terminada else "Pendiente"
        return (f"[{self.__id_actividad}] {self.__descripcion} | "
                f"{self.__fecha_inicio:%d/%m/%Y} -> {self.__fecha_fin:%d/%m/%Y} "
                f"({self.duracion_dias()} dias) - {estado}")


class Proyecto:
    def __init__(self, id_proyecto, nombre, descripcion, fecha_inicio, fecha_fin):
        if fecha_fin < fecha_inicio:
            raise ValueError("La fecha fin no puede ser anterior a la fecha inicio.")
        self.__id_proyecto = id_proyecto
        self.__nombre = nombre
        self.__descripcion = descripcion
        self.__fecha_inicio = fecha_inicio
        self.__fecha_fin = fecha_fin
        self.__estado = EstadoProyecto.REGISTRADO
        self.__actividades = []
        self.__responsable = None

    @property
    def id_proyecto(self):
        return self.__id_proyecto

    @property
    def nombre(self):
        return self.__nombre

    @property
    def descripcion(self):
        return self.__descripcion

    @property
    def fecha_inicio(self):
        return self.__fecha_inicio

    @property
    def fecha_fin(self):
        return self.__fecha_fin

    @property
    def estado(self):
        return self.__estado

    @property
    def actividades(self):
        return list(self.__actividades)

    @property
    def responsable(self):
        return self.__responsable

    @responsable.setter
    def responsable(self, responsable):
        self.__responsable = responsable

    def hay_cruce(self, act):
        return any(act.se_cruza_con(a) for a in self.__actividades)

    def agregar_actividad(self, act):
        if self.__estado == EstadoProyecto.TERMINADO:
            raise ValueError("No se pueden agregar actividades a un proyecto terminado.")
        if act.fecha_inicio < self.__fecha_inicio or act.fecha_fin > self.__fecha_fin:
            raise ValueError("La actividad debe estar dentro de las fechas del proyecto.")
        if self.hay_cruce(act):
            raise ValueError("La actividad se cruza con otra ya registrada.")
        self.__actividades.append(act)

    def todas_terminadas(self):
        return bool(self.__actividades) and all(a.terminada for a in self.__actividades)

    def cambiar_estado(self, nuevo):
        if not isinstance(nuevo, EstadoProyecto):
            raise ValueError("El estado indicado no es válido.")

        if self.__estado == EstadoProyecto.TERMINADO and nuevo != EstadoProyecto.TERMINADO:
            raise ValueError("Un proyecto terminado no puede volver a un estado anterior.")

        transiciones = {
            EstadoProyecto.REGISTRADO: {EstadoProyecto.REGISTRADO, EstadoProyecto.EN_PROCESO},
            EstadoProyecto.EN_PROCESO: {EstadoProyecto.EN_PROCESO, EstadoProyecto.TERMINADO},
            EstadoProyecto.TERMINADO: {EstadoProyecto.TERMINADO},
        }
        if nuevo not in transiciones[self.__estado]:
            raise ValueError(
                f"No se permite cambiar de {self.__estado.value} a {nuevo.value}."
            )
        if nuevo == EstadoProyecto.TERMINADO and not self.todas_terminadas():
            raise ValueError("No se puede terminar: hay actividades pendientes (o no hay ninguna).")
        self.__estado = nuevo

    def calcular_porcentaje_avance(self):
        if not self.__actividades:
            return 0.0
        completadas = sum(1 for a in self.__actividades if a.terminada)
        return completadas / len(self.__actividades) * 100

    def __str__(self):
        resp = self.__responsable.nombre_completo() if self.__responsable else "Sin asignar"
        return (f"[{self.__id_proyecto}] {self.__nombre} | "
                f"{self.__fecha_inicio:%d/%m/%Y} -> {self.__fecha_fin:%d/%m/%Y} | "
                f"Estado: {self.__estado.value} | Avance: {self.calcular_porcentaje_avance():.1f}% | "
                f"Responsable: {resp}")


class Servicio:
    def __init__(self, id_servicio, descripcion, fecha_solicitud, fecha_entrega, cliente):
        if fecha_entrega < fecha_solicitud:
            raise ValueError("La fecha de entrega no puede ser anterior a la solicitud.")
        self.__id_servicio = id_servicio
        self.__descripcion = descripcion
        self.__fecha_solicitud = fecha_solicitud
        self.__fecha_entrega = fecha_entrega
        self.__entregado = False
        self.__cliente = cliente
        self.__proyectos = []

    @property
    def id_servicio(self):
        return self.__id_servicio

    @property
    def descripcion(self):
        return self.__descripcion

    @property
    def fecha_solicitud(self):
        return self.__fecha_solicitud

    @property
    def fecha_entrega(self):
        return self.__fecha_entrega

    @property
    def entregado(self):
        return self.__entregado

    @property
    def cliente(self):
        return self.__cliente

    @property
    def proyectos(self):
        return list(self.__proyectos)

    def agregar_proyecto(self, proyecto):
        if self.__entregado:
            raise ValueError("No se pueden agregar proyectos a un servicio entregado.")
        if proyecto.fecha_inicio < self.__fecha_solicitud or proyecto.fecha_fin > self.__fecha_entrega:
            raise ValueError("Las fechas del proyecto deben estar dentro del periodo del servicio.")
        if proyecto in self.__proyectos:
            raise ValueError("Este proyecto ya está registrado en el servicio.")
        self.__proyectos.append(proyecto)

    def listo_para_entrega(self):
        return bool(self.__proyectos) and all(
            p.estado == EstadoProyecto.TERMINADO for p in self.__proyectos
        )

    def marcar_entregado(self):
        if self.__entregado:
            raise ValueError("El servicio ya fue marcado como entregado.")
        if not self.listo_para_entrega():
            raise ValueError("El servicio aún tiene proyectos sin terminar (o no tiene proyectos).")
        self.__entregado = True

    def __str__(self):
        estado = "Entregado" if self.__entregado else "Pendiente"
        return (f"[{self.__id_servicio}] {self.__descripcion} | Solicitado: {self.__fecha_solicitud:%d/%m/%Y} | "
                f"Entrega: {self.__fecha_entrega:%d/%m/%Y} | {estado}")


class Persona:
    def __init__(self, id_persona, nombre, apellido, dni, telefono, email):
        self.__id_persona = id_persona
        self.__nombre = nombre
        self.__apellido = apellido
        self.__dni = dni
        self.__telefono = telefono
        self.__email = email

    @property
    def id_persona(self):
        return self.__id_persona

    @property
    def nombre(self):
        return self.__nombre

    @property
    def apellido(self):
        return self.__apellido

    @property
    def dni(self):
        return self.__dni

    @property
    def telefono(self):
        return self.__telefono

    @property
    def email(self):
        return self.__email

    def nombre_completo(self):
        return f"{self.__nombre} {self.__apellido}"


class Cliente(Persona):
    def __init__(self, id_persona, nombre, apellido, dni, telefono, email,
                 id_cliente, razon_social, direccion):
        super().__init__(id_persona, nombre, apellido, dni, telefono, email)
        self.__id_cliente = id_cliente
        self.__razon_social = razon_social
        self.__direccion = direccion
        self.__servicios = []

    @property
    def id_cliente(self):
        return self.__id_cliente

    @property
    def razon_social(self):
        return self.__razon_social

    @property
    def direccion(self):
        return self.__direccion

    def agregar_servicio(self, servicio):
        if servicio not in self.__servicios:
            self.__servicios.append(servicio)

    def listar_servicios(self):
        return list(self.__servicios)

    def __str__(self):
        return (f"[{self.__id_cliente}] {self.nombre_completo()} | DNI: {self.dni} | "
                f"{self.__razon_social} | {self.__direccion}")


class Usuario(Persona):
    def __init__(self, id_persona, nombre, apellido, dni, telefono, email,
                 id_usuario, username, password, activo=True):
        super().__init__(id_persona, nombre, apellido, dni, telefono, email)
        self.__id_usuario = id_usuario
        self.__username = username
        self.__password_salt = os.urandom(16)
        self.__password_hash = self.__hash_password(password, self.__password_salt)
        self.__activo = activo

    @staticmethod
    def __hash_password(password, salt):
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)

    @property
    def id_usuario(self):
        return self.__id_usuario

    @property
    def username(self):
        return self.__username

    @property
    def activo(self):
        return self.__activo

    def autenticar(self, user, clave):
        if not self.__activo or user != self.__username:
            return False
        intento = self.__hash_password(clave, self.__password_salt)
        return hmac.compare_digest(intento, self.__password_hash)

    def menu(self):
        raise NotImplementedError("Cada tipo de usuario define su propio menú.")


class Responsable(Usuario):
    def __init__(self, id_persona, nombre, apellido, dni, telefono, email,
                 id_usuario, username, password, especialidad):
        super().__init__(id_persona, nombre, apellido, dni, telefono, email,
                         id_usuario, username, password)
        self.__especialidad = especialidad
        self.__proyectos = []

    @property
    def especialidad(self):
        return self.__especialidad

    @property
    def proyectos(self):
        return list(self.__proyectos)

    def esta_libre(self, f_ini, f_fin):
        for p in self.__proyectos:
            if p.estado != EstadoProyecto.TERMINADO and p.fecha_inicio <= f_fin and f_ini <= p.fecha_fin:
                return False
        return True

    def asignar_proyecto(self, proyecto):
        if proyecto.estado == EstadoProyecto.TERMINADO:
            raise ValueError("No se puede asignar un responsable a un proyecto terminado.")
        if proyecto.responsable is not None:
            raise ValueError("Ese proyecto ya tiene responsable.")
        if not self.esta_libre(proyecto.fecha_inicio, proyecto.fecha_fin):
            raise ValueError("El responsable no está libre en las fechas de ese proyecto.")
        self.__proyectos.append(proyecto)
        proyecto.responsable = self

    def _verificar_proyecto_propio(self, proyecto):
        if proyecto not in self.__proyectos:
            raise ValueError("Ese proyecto no está asignado a este responsable.")

    def registrar_actividad(self, proyecto, act):
        self._verificar_proyecto_propio(proyecto)
        proyecto.agregar_actividad(act)

    def cambiar_estado(self, proyecto, estado):
        self._verificar_proyecto_propio(proyecto)
        proyecto.cambiar_estado(estado)

    def __str__(self):
        return f"[{self.id_usuario}] {self.nombre_completo()} | {self.__especialidad} | user: {self.username}"

    def menu(self):
        while True:
            print(f"\n=== MENU RESPONSABLE: {self.nombre_completo()} ===")
            print("1. Ver mis proyectos")
            print("2. Registrar actividad en un proyecto")
            print("3. Marcar actividad como terminada")
            print("4. Cambiar estado de un proyecto")
            print("5. Ver actividades de un proyecto")
            print("0. Cerrar sesion")
            op = leer_opcion("Opcion: ", 0, 5)

            if op == 0:
                return
            if not self.__proyectos:
                print("\nAun no tienes proyectos asignados.")
                continue
            if op == 1:
                print()
                for p in self.__proyectos:
                    print(p)
                continue

            proyecto = elegir(self.__proyectos, "Elige un proyecto")
            if proyecto is None:
                continue
            try:
                if op == 2:
                    self.__ui_registrar_actividad(proyecto)
                elif op == 3:
                    self.__ui_marcar_terminada(proyecto)
                elif op == 4:
                    self.__ui_cambiar_estado(proyecto)
                elif op == 5:
                    self.__ui_ver_actividades(proyecto)
            except ValueError as e:
                print(f"\n  ERROR: {e}")

    def __ui_registrar_actividad(self, proyecto):
        descripcion = leer_texto("Descripcion de la actividad: ")
        f_ini = leer_fecha("Fecha inicio")
        f_fin = leer_fecha("Fecha fin")
        act = Actividad(len(proyecto.actividades) + 1, descripcion, f_ini, f_fin)
        self.registrar_actividad(proyecto, act)
        print("\n  Actividad registrada.")

    def __ui_marcar_terminada(self, proyecto):
        pendientes = [a for a in proyecto.actividades if not a.terminada]
        act = elegir(pendientes, "Actividad a terminar")
        if act is None:
            return
        act.marcar_terminada()
        print("\n  Actividad marcada como terminada.")
        if proyecto.todas_terminadas():
            print("  Todas las actividades estan terminadas: ya puedes pasar el proyecto a TERMINADO (opcion 4).")

    def __ui_cambiar_estado(self, proyecto):
        estado = elegir(list(EstadoProyecto), "Nuevo estado", lambda e: e.value)
        if estado is None:
            return
        self.cambiar_estado(proyecto, estado)
        print(f"\n  Estado actualizado a {estado.value}.")

    def __ui_ver_actividades(self, proyecto):
        print(f"\n{proyecto}")
        if not proyecto.actividades:
            print("  (sin actividades)")
        for a in proyecto.actividades:
            print("  ", a)


class Secretario(Usuario):
    def __init__(self, id_persona, nombre, apellido, dni, telefono, email,
                 id_usuario, username, password, codigo, sistema):
        super().__init__(id_persona, nombre, apellido, dni, telefono, email,
                         id_usuario, username, password)
        self.__codigo = codigo
        self.__sistema = sistema

    @property
    def codigo(self):
        return self.__codigo

    def registrar_cliente(self, nombre, apellido, dni, telefono, email, razon_social, direccion):
        s = self.__sistema
        if s.buscar_por_dni(dni):
            raise ValueError("Ya existe una persona registrada con ese DNI.")
        cliente = Cliente(s.nuevo_id("persona"), nombre, apellido, dni, telefono, email,
                          s.nuevo_id("cliente"), razon_social, direccion)
        s.clientes.append(cliente)
        return cliente

    def registrar_responsable(self, nombre, apellido, dni, telefono, email,
                              username, password, especialidad):
        s = self.__sistema
        if s.buscar_por_dni(dni):
            raise ValueError("Ya existe una persona registrada con ese DNI.")
        if s.username_existe(username):
            raise ValueError("Ese nombre de usuario ya está en uso.")
        resp = Responsable(s.nuevo_id("persona"), nombre, apellido, dni, telefono, email,
                           s.nuevo_id("usuario"), username, password, especialidad)
        s.responsables.append(resp)
        return resp

    def registrar_secretario(self, nombre, apellido, dni, telefono, email,
                             username, password, codigo):
        s = self.__sistema
        if s.buscar_por_dni(dni):
            raise ValueError("Ya existe una persona registrada con ese DNI.")
        if s.username_existe(username):
            raise ValueError("Ese nombre de usuario ya está en uso.")
        sec = Secretario(s.nuevo_id("persona"), nombre, apellido, dni, telefono, email,
                         s.nuevo_id("usuario"), username, password, codigo, s)
        s.secretarios.append(sec)
        return sec

    def registrar_servicio(self, cliente, descripcion, fecha_solicitud, fecha_entrega):
        s = self.__sistema
        if cliente not in s.clientes:
            raise ValueError("El cliente seleccionado no está registrado en el sistema.")
        servicio = Servicio(s.nuevo_id("servicio"), descripcion, fecha_solicitud, fecha_entrega, cliente)
        s.servicios.append(servicio)
        cliente.agregar_servicio(servicio)
        return servicio

    def registrar_proyecto(self, servicio, nombre, descripcion, fecha_inicio, fecha_fin):
        s = self.__sistema
        if servicio not in s.servicios:
            raise ValueError("El servicio seleccionado no está registrado en el sistema.")
        proyecto = Proyecto(s.nuevo_id("proyecto"), nombre, descripcion, fecha_inicio, fecha_fin)
        servicio.agregar_proyecto(proyecto)
        s.proyectos.append(proyecto)
        return proyecto

    def asignar_responsable(self, proyecto, responsable):
        if proyecto not in self.__sistema.proyectos:
            raise ValueError("El proyecto no está registrado en el sistema.")
        if responsable not in self.__sistema.responsables:
            raise ValueError("El responsable no está registrado en el sistema.")
        if proyecto.responsable is not None:
            raise ValueError("Ese proyecto ya tiene responsable.")
        responsable.asignar_proyecto(proyecto)
        proyecto.cambiar_estado(EstadoProyecto.EN_PROCESO)

    def menu(self):
        s = self.__sistema
        while True:
            print(f"\n=== MENU SECRETARIO: {self.nombre_completo()} ===")
            print("1. Registrar cliente")
            print("2. Registrar responsable")
            print("3. Registrar servicio")
            print("4. Registrar proyecto (dentro de un servicio)")
            print("5. Asignar responsable a un proyecto")
            print("6. Listar clientes")
            print("7. Listar servicios y proyectos")
            print("8. Marcar servicio como entregado")
            print("9. Registrar secretario")
            print("0. Cerrar sesion")
            op = leer_opcion("Opcion: ", 0, 9)
            try:
                if op == 0:
                    return
                elif op == 1:
                    self.__ui_cliente()
                elif op == 2:
                    self.__ui_responsable()
                elif op == 3:
                    self.__ui_servicio(s)
                elif op == 4:
                    self.__ui_proyecto(s)
                elif op == 5:
                    self.__ui_asignar(s)
                elif op == 6:
                    self.__ui_listar_clientes(s)
                elif op == 7:
                    self.__ui_listar_servicios(s)
                elif op == 8:
                    self.__ui_entregar(s)
                elif op == 9:
                    self.__ui_secretario()
            except ValueError as e:
                print(f"\n  ERROR: {e}")

    def __ui_cliente(self):
        print("\n-- Nuevo cliente --")
        datos = leer_datos_persona()
        razon = leer_texto("Razon social: ")
        direccion = leer_texto("Direccion: ")
        c = self.registrar_cliente(*datos, razon, direccion)
        print(f"\n  Cliente registrado con ID {c.id_cliente}.")

    def __ui_responsable(self):
        print("\n-- Nuevo responsable --")
        datos = leer_datos_persona()
        username = leer_texto("Username: ")
        password = leer_texto("Password: ")
        especialidad = leer_texto("Especialidad: ")
        r = self.registrar_responsable(*datos, username, password, especialidad)
        print(f"\n  Responsable registrado con ID {r.id_usuario}.")

    def __ui_secretario(self):
        print("\n-- Nuevo secretario --")
        datos = leer_datos_persona()
        username = leer_texto("Username: ")
        password = leer_texto("Password: ")
        codigo = leer_texto("Codigo de secretario: ")
        sec = self.registrar_secretario(*datos, username, password, codigo)
        print(f"\n  Secretario registrado con ID {sec.id_usuario}.")

    def __ui_servicio(self, s):
        cliente = elegir(s.clientes, "Cliente que solicita el servicio")
        if cliente is None:
            return
        descripcion = leer_texto("Descripcion del servicio: ")
        f_sol = leer_fecha("Fecha de solicitud")
        f_ent = leer_fecha("Fecha de entrega")
        sv = self.registrar_servicio(cliente, descripcion, f_sol, f_ent)
        print(f"\n  Servicio registrado con ID {sv.id_servicio}.")

    def __ui_proyecto(self, s):
        servicio = elegir([x for x in s.servicios if not x.entregado], "Servicio al que pertenece")
        if servicio is None:
            return
        nombre = leer_texto("Nombre del proyecto: ")
        descripcion = leer_texto("Descripcion: ")
        f_ini = leer_fecha("Fecha inicio")
        f_fin = leer_fecha("Fecha fin")
        p = self.registrar_proyecto(servicio, nombre, descripcion, f_ini, f_fin)
        print(f"\n  Proyecto registrado con ID {p.id_proyecto}.")

    def __ui_asignar(self, s):
        proyecto = elegir([p for p in s.proyectos if p.responsable is None and p.estado != EstadoProyecto.TERMINADO],
                          "Proyecto sin responsable")
        if proyecto is None:
            return
        libres = [r for r in s.responsables if r.esta_libre(proyecto.fecha_inicio, proyecto.fecha_fin)]
        resp = elegir(libres, "Responsable disponible en esas fechas")
        if resp is None:
            return
        self.asignar_responsable(proyecto, resp)
        print(f"\n  {resp.nombre_completo()} asignado a '{proyecto.nombre}' (estado: EN PROCESO).")

    def __ui_listar_clientes(self, s):
        print("\n-- Clientes --")
        if not s.clientes:
            print("  (no hay clientes)")
        for c in s.clientes:
            print(c)
            for sv in c.listar_servicios():
                print("     ->", sv)

    def __ui_listar_servicios(self, s):
        print("\n-- Servicios --")
        if not s.servicios:
            print("  (no hay servicios)")
        for sv in s.servicios:
            print(f"{sv}  | Cliente: {sv.cliente.nombre_completo()}")
            for p in sv.proyectos:
                print("     ->", p)

    def __ui_entregar(self, s):
        servicio = elegir([x for x in s.servicios if not x.entregado], "Servicio a entregar")
        if servicio is None:
            return
        servicio.marcar_entregado()
        print("\n  Servicio marcado como entregado.")


class Sistema:
    def __init__(self):
        self.clientes = []
        self.responsables = []
        self.secretarios = []
        self.servicios = []
        self.proyectos = []
        self.__contadores = {}

    def nuevo_id(self, clave):
        self.__contadores[clave] = self.__contadores.get(clave, 0) + 1
        return self.__contadores[clave]

    def buscar_por_dni(self, dni):
        personas = self.clientes + self.responsables + self.secretarios
        return next((p for p in personas if p.dni == dni), None)

    def username_existe(self, username):
        return any(u.username == username for u in self.secretarios + self.responsables)

    def login(self, user, clave):
        for u in self.secretarios + self.responsables:
            if u.autenticar(user, clave):
                return u
        return None

    def crear_secretario_inicial(self):
        if self.username_existe("admin"):
            raise ValueError("Ya existe el usuario admin.")
        sec = Secretario(self.nuevo_id("persona"), "Admin", "Sistema", "00000000", "-", "-",
                         self.nuevo_id("usuario"), "admin", "admin123", "SEC-001", self)
        self.secretarios.append(sec)


def leer_texto(mensaje):
    while True:
        t = input(mensaje).strip()
        if t:
            return t
        print("  Este campo es obligatorio.")


def leer_opcion(mensaje, minimo, maximo):
    while True:
        t = input(mensaje).strip()
        if t.isdigit() and minimo <= int(t) <= maximo:
            return int(t)
        print(f"  Ingresa un numero entre {minimo} y {maximo}.")


def leer_fecha(mensaje):
    while True:
        t = input(f"{mensaje} (dd/mm/aaaa): ").strip()
        try:
            return datetime.strptime(t, "%d/%m/%Y").date()
        except ValueError:
            print("  Fecha invalida. Ejemplo: 25/10/2026")


def leer_datos_persona():
    nombre = leer_texto("Nombre: ")
    apellido = leer_texto("Apellido: ")
    while True:
        dni = leer_texto("DNI (8 digitos): ")
        if dni.isdigit() and len(dni) == 8:
            break
        print("  El DNI debe tener 8 digitos.")
    telefono = leer_texto("Telefono: ")
    while True:
        email = leer_texto("Email: ")
        if "@" in email:
            break
        print("  Email invalido.")
    return nombre, apellido, dni, telefono, email


def elegir(lista, titulo, describir=str):
    if not lista:
        print("\n  No hay elementos disponibles para esta accion.")
        return None
    print(f"\n{titulo}:")
    for i, item in enumerate(lista, 1):
        print(f"  {i}. {describir(item)}")
    print("  0. Cancelar")
    n = leer_opcion("Opcion: ", 0, len(lista))
    return None if n == 0 else lista[n - 1]


def main():
    sistema = Sistema()
    sistema.crear_secretario_inicial()

    print("=== SISTEMA DE GESTION DE SERVICIOS Y PROYECTOS ===")
    print("(Primer ingreso: usuario 'casa', clave 'casa123')")

    while True:
        print("\n--- INICIAR SESION ---  (escribe 'salir' como usuario para cerrar el programa)")
        user = input("Usuario: ").strip()
        if user.lower() == "salir":
            print("Hasta luego.")
            break
        clave = input("Clave: ").strip()
        usuario = sistema.login(user, clave)
        if usuario is None:
            print("  Credenciales incorrectas.")
            continue
        usuario.menu()


if __name__ == "__main__":
    main()
