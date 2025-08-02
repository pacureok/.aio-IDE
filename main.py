import re
import os
import shutil

# Placeholder para los estados de los pines de (esp)
# En una implementación real, esto vendría de un intérprete de (esp)
# Si 'deploy_success' es "si", el archivo pre_deploy_log.txt se borrará.
# Si 'deploy_success' es "no", el archivo pre_deploy_log.txt NO se borrará.
esp_pin_states = {
    "deploy_success": "no", # Por defecto para demostración: no borra el log
    "n": "si",
    "p": "no",
}

# Función para leer el bloque <meta> y extraer configuraciones
def parse_meta_block(content):
    meta_match = re.search(r'<meta>(.*?)</meta>', content, re.DOTALL)
    if meta_match:
        meta_content = meta_match.group(1).strip()
        config = {}
        for line in meta_content.split(','):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                if value.startswith('[') and value.endswith(']'):
                    config[key] = [item.strip().strip('"') for item in value[1:-1].split(',')]
                else:
                    config[key] = value.strip('"')
        return config
    return {}

# Función para parsear el bloque <crea>
def parse_crea_block(crea_content, output_dir):
    lines = crea_content.split('\n')
    
    print("\n--- Procesando comandos <crea> ---")
    for line in lines:
        cmd = line.strip()
        if not cmd or cmd.startswith('#'):
            continue

        cmd_without_comment = cmd.split('#', 1)[0].strip()

        # Comando $crea=file
        create_match = re.match(r'\$crea=file\s+Name="([^"]+)"\s*(%extencion\s*\.([^,\s]+))?\s*(%Not_extencion)?(,)?', cmd_without_comment)
        if create_match:
            name = create_match.group(1)
            extension = create_match.group(3)
            not_extension_flag = create_match.group(4)

            # Reemplaza '_' por '/' en el nombre para la ruta del sistema de archivos,
            # lo que permite especificar subdirectorios como "Project_Assets/logo_aio"
            file_or_dir_path_relative = name.replace('_', os.sep) # Usar os.sep para compatibilidad OS
            full_path_target = os.path.join(output_dir, file_or_dir_path_relative)
            
            if not_extension_flag:
                # Si es %Not_extencion, crear un directorio
                if not os.path.exists(full_path_target):
                    os.makedirs(full_path_target)
                    print(f"Directorio creado: '{full_path_target}'")
                else:
                    print(f"Directorio ya existe: '{full_path_target}'")
            else:
                # Crear un archivo con o sin extensión
                final_file_path = f"{full_path_target}.{extension}" if extension else full_path_target
                # Asegurarse de que el directorio padre exista antes de crear el archivo
                os.makedirs(os.path.dirname(final_file_path), exist_ok=True)
                try:
                    with open(final_file_path, 'w', encoding='utf-8') as f:
                        f.write(f"# Archivo creado por Aio: {os.path.basename(final_file_path)}\n")
                    print(f"Archivo creado: '{final_file_path}'")
                except Exception as e:
                    print(f"Error al crear archivo '{final_file_path}': {e}")
            continue

        # Comando %borra
        delete_match = re.match(r'%borra=(?:Name="([^"]+)"|file="([^"]+)")(?:\s*(%all))?(?:\s*%([^,\s]+(?:,[^,\s]+)*))?(?:\s*&con\s*"([^"]+)")?(,)?', cmd_without_comment)
        if delete_match:
            name_to_delete = delete_match.group(1)
            path_to_delete_relative = delete_match.group(2) # Esta es la ruta ya relativa al output_dir
            all_flag = delete_match.group(3)
            specific_files_str = delete_match.group(4)
            conditional_logic_pin_name = delete_match.group(5)

            target_path_base = ""
            if name_to_delete:
                target_path_base = os.path.join(output_dir, name_to_delete.replace('_', os.sep))
            elif path_to_delete_relative: # Si se usa 'file=', la ruta ya incluye el 'build/' o 'aio_demo_build/'
                target_path_base = path_to_delete_relative # Usamos la ruta tal cual viene, asumiendo que es absoluta o relativa desde la raíz del output_dir
                if not os.path.isabs(target_path_base):
                    target_path_base = os.path.join(output_dir, target_path_base)
            else:
                print(f"Error: Comando %borra incompleto (falta Name o file): {cmd}")
                continue
            
            # Evaluar la condición &con
            condition_met = True
            if conditional_logic_pin_name:
                pin_name = conditional_logic_pin_name.strip('"')
                if pin_name in esp_pin_states:
                    # La condición para borrar se cumple si el pin es "si" para borrado,
                    # o "no" para no borrado, según la lógica del usuario.
                    # Aquí la lógica del usuario para 'deploy_success': borra si es 'si'.
                    # Es decir, si 'deploy_success' es 'si', condition_met = True.
                    # Si 'deploy_success' es 'no', condition_met = False.
                    # Asumiendo %borra=file="pre_deploy_log.txt" &con "deploy_success"
                    # Se borra si deploy_success == "si"
                    if pin_name == "deploy_success":
                        if esp_pin_states[pin_name] == "no": # Si el despliegue NO fue exitoso
                            condition_met = False
                            print(f"Condición '{pin_name}' no se cumple (estado '{esp_pin_states[pin_name]}'). Borrado no ejecutado para '{target_path_base}'.")
                    else: # Para otros pines, mantiene la lógica anterior si aplica
                        if (pin_name == "n" and esp_pin_states[pin_name] == "si") or \
                           (pin_name == "p" and esp_pin_states[pin_name] == "no"):
                            condition_met = False
                            print(f"Condición '{pin_name}' no se cumple (estado '{esp_pin_states[pin_name]}'). Borrado no ejecutado para '{target_path_base}'.")
                else:
                    print(f"Advertencia: Pin '{pin_name}' no encontrado en estados de (esp). No se puede evaluar condición. Asumiendo TRUE.")
            
            if not condition_met:
                continue # Saltar el borrado si la condición no se cumple

            # Ejecutar el borrado
            if all_flag: # %all
                if os.path.exists(target_path_base):
                    if os.path.isdir(target_path_base):
                        shutil.rmtree(target_path_base)
                        print(f"Directorio y contenido borrados: '{target_path_base}'")
                    else:
                        os.remove(target_path_base)
                        print(f"Archivo borrado: '{target_path_base}'")
                else:
                    print(f"Advertencia: '{target_path_base}' no encontrado para borrado %all.")
            elif specific_files_str: # %file1,file2,...
                files_to_delete = [f.strip() for f in specific_files_str.split(',')]
                for f_name in files_to_delete:
                    file_to_delete_path = os.path.join(os.path.dirname(target_path_base), f_name.replace('_', os.sep))
                    if os.path.exists(file_to_delete_path) and os.path.isfile(file_to_delete_path):
                        os.remove(file_to_delete_path)
                        print(f"Archivo borrado: '{file_to_delete_path}'")
                    else:
                        print(f"Advertencia: '{file_to_delete_path}' no encontrado o no es un archivo para borrado.")
            elif name_to_delete: # %borra=Name="ejemplo.js" (borra solo ese archivo en output_dir)
                if os.path.exists(target_path_base) and os.path.isfile(target_path_base):
                    os.remove(target_path_base)
                    print(f"Archivo borrado: '{target_path_base}'")
                else:
                    print(f"Advertencia: '{target_path_base}' no encontrado para borrado por nombre.")
            else:
                print(f"Error: Comando %borra válido, pero no especificó qué borrar (ej. %all o archivos): {cmd}")
            continue
            
        print(f"Advertencia: Comando <crea> no reconocido o mal formado: '{cmd}'")

# Esta función lee un archivo .aio y extrae los bloques de código
def parse_aio_file(file_path):
    print(f"\n--- Procesando archivo: {file_path} ---")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: El archivo '{file_path}' no fue encontrado. Asegúrese de que existe y el nombre es correcto.")
        return None, {}
    except Exception as e:
        print(f"Error al leer el archivo '{file_path}': {e}")
        return None, {}

    config = parse_meta_block(content)

    blocks = {
        'html': re.findall(r'<video>(.*?)</video>', content, re.DOTALL),
        'css': re.findall(r'<cs>(.*?)</cs>', content, re.DOTALL),
        'js': re.findall(r'<tp>(.*?)</tp>', content, re.DOTALL),
        'esp': re.findall(r'\(esp\)(.*?)\(/esp\)', content, re.DOTALL),
        'ing': re.findall(r'<ING>(.*?)</ING>', content, re.DOTALL),
        'net': re.findall(r'<net>(.*?)</net>', content, re.DOTALL),
        'lua': re.findall(r'<lua>(.*?)</lua>', content, re.DOTALL),
        'pat': re.findall(r'\(pat\)(.*?)\(/pat\)', content, re.DOTALL),
        'rs': re.findall(r'<rs>(.*?)</rs>', content, re.DOTALL),
        'go': re.findall(r'<go>(.*?)</go>', content, re.DOTALL),
        'sql': re.findall(r'<sql>(.*?)</sql>', content, re.DOTALL),
        'meta_block': re.findall(r'<meta>(.*?)</meta>', content, re.DOTALL),
        'crea_block': re.findall(r'<crea>(.*?)</crea>', content, re.DOTALL),
        'sln': re.findall(r'<sln>(.*?)</sln>', content, re.DOTALL),
        'xaml': re.findall(r'<xaml>(.*?)</xaml>', content, re.DOTALL),
        'config': re.findall(r'<config>(.*?)</config>', content, re.DOTALL),
        'csproj': re.findall(r'<csproj>(.*?)</csproj>', content, re.DOTALL),
    }
    return blocks, config

# Esta función guardará cada bloque en un archivo separado, gestionando la estructura de VS
def save_blocks_to_files(blocks, config, base_name):
    output_dir = config.get('output_dir', 'build') # Valor por defecto si no está en meta
    
    # Crear el directorio base de salida si no existe
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Directorio de salida principal '{output_dir}/' creado.")
    else:
        print(f"Directorio de salida principal '{output_dir}/' ya existe.")

    # Diccionario para mapear los bloques a sus rutas y nombres de archivo
    # Esto es crucial para la flexibilidad y la estructura de VS
    file_map = []

    # Web files (Frontend) - siempre en el directorio raíz de salida para una web
    if blocks['html']:
        file_map.append({'content': blocks['html'][0], 'path': 'index.html', 'type': 'html'})
    if blocks['css']:
        file_map.append({'content': blocks['css'][0], 'path': 'style.css', 'type': 'css'})
    if blocks['js']:
        file_map.append({'content': blocks['js'][0], 'path': 'script.js', 'type': 'js'})

    # DSL files
    if blocks['esp']:
        file_map.append({'content': blocks['esp'][0], 'path': f'logic_{base_name}.esp', 'type': 'dsl'})
    if blocks['ing']:
        file_map.append({'content': blocks['ing'][0], 'path': f'logic_{base_name}.ing', 'type': 'dsl'})
    if blocks['pat']:
        file_map.append({'content': blocks['pat'][0], 'path': f'patterns_{base_name}.pat', 'type': 'dsl'})

    # .NET Solution File (.sln)
    if blocks['sln']:
        file_map.append({'content': blocks['sln'][0], 'path': f'{base_name}.sln', 'type': 'sln'})

    # .NET Projects and associated files (C#, XAML, Config, CSPROJ)
    # Asumimos que dentro de <csproj> y <net> y <xaml> el usuario indicará la ruta relativa
    # al output_dir y dentro del proyecto .NET
    
    # Manejo de múltiples CSPROJ (cada uno es un proyecto .NET)
    # Se asume que el contenido de <csproj> contiene un solo .csproj,
    # y el nombre del archivo se infiere del contenido o se especifica aquí.
    # Esta es una simplificación; idealmente, el AIO especificaría el nombre del archivo csproj
    # o la ruta del proyecto.
    
    # Los bloques <net>, <xaml>, <config>, <csproj> pueden contener MÚLTIPLES archivos
    # o lógicas para diferentes proyectos. Tu Regex los agrupa en una lista por bloque.
    # Debemos dividir el contenido de estos bloques si contienen varios archivos
    # o si representan distintos proyectos.

    # Por la forma actual de tus regex, cada bloque (net, xaml, csproj) captura todo su contenido.
    # Necesitamos una forma de saber qué parte de <net> va a qué archivo C# y en qué proyecto.
    # La solución más simple por ahora es asumir que el ejemplo de <net> es para varios archivos
    # y el <csproj> también para varios.

    # Estrategia:
    # 1. Procesar el bloque <csproj> para extraer la información de cada proyecto y su ruta.
    # 2. Iterar sobre el contenido de <net>, <xaml>, <config> para identificar los archivos
    #    y su ubicación. Esto es el punto más complejo de la automatización.

    # Para este ejemplo, haremos una inferencia simple basada en el contenido del .aio
    # que proporcionaste para la demostración de VS. Esto significa que si un bloque <net>
    # contiene el código de varios archivos C#, los dividiremos y los guardaremos.

    if blocks['csproj']:
        # Cada contenido de csproj debe ser un archivo .csproj
        # Por simplicidad, asumiremos que cada elemento en blocks['csproj'] es el contenido de un .csproj.
        # El nombre del archivo .csproj y la carpeta del proyecto se extraen del contenido.
        for csproj_content in blocks['csproj']:
            # Extraer el nombre del proyecto del csproj (Sdk="Microsoft.NET.Sdk")
            # Buscar el nombre del proyecto en el XML (no infalible, pero para el demo)
            project_name_match = re.search(r'<RootNamespace>(.*?)</RootNamespace>', csproj_content, re.DOTALL)
            project_name = project_name_match.group(1).strip() if project_name_match else f'UnnamedProject_{len(file_map)}'
            
            # Buscar si es un tipo de salida (WinExe, Exe, Library) para el nombre de .csproj
            output_type_match = re.search(r'<OutputType>(.*?)</OutputType>', csproj_content)
            output_type = output_type_match.group(1).strip() if output_type_match else ''

            # Determinar el nombre del archivo .csproj (ej. ApiProject.csproj)
            csproj_filename = f"{project_name}.csproj"

            # Determinar la carpeta del proyecto (generalmente igual al nombre del proyecto)
            project_folder = project_name
            
            csproj_path = os.path.join(project_folder, csproj_filename)
            file_map.append({'content': csproj_content, 'path': csproj_path, 'type': 'csproj'})


    # Manejar archivos C# (<net>)
    if blocks['net']:
        # Se asume que dentro del bloque <net> hay comentarios que indican la ruta y el nombre del archivo
        # // File: vs_solution/ApiProject/Controllers/ValuesController.cs
        # Esta es una estrategia para inferir los nombres de archivo desde el AIO
        net_content = blocks['net'][0] # Tomamos el primer (y único) bloque <net> completo
        # Dividir el contenido por las líneas de comentario que indican el archivo
        cs_files = re.split(r'^\s*//\s*File:\s*vs_solution/([^/\\]+)/(.+\.cs)\s*$', net_content, flags=re.MULTILINE)
        
        # El primer elemento de cs_files será vacío o el contenido antes del primer archivo
        # Los elementos pares son los nombres de las carpetas de proyecto, impares son rutas completas del archivo
        if len(cs_files) > 1: # Si hay al menos un archivo detectado
            for i in range(1, len(cs_files), 3): # Saltar el primer elemento vacío, luego 3 en 3
                if i+2 <= len(cs_files): # Asegurarse de que hay suficiente contenido para un archivo
                    project_folder = cs_files[i].strip() # Ej: ApiProject
                    relative_path_in_project = cs_files[i+1].strip() # Ej: Controllers/ValuesController.cs
                    cs_code_content = cs_files[i+2].strip()

                    # Construir la ruta completa para el archivo C#
                    full_cs_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': cs_code_content, 'path': full_cs_path, 'type': 'cs'})

    # Manejar archivos XAML (<xaml>)
    if blocks['xaml']:
        # Similar a <net>, buscar la ruta indicada en comentarios
        xaml_content = blocks['xaml'][0]
        xaml_files = re.split(r'', xaml_content, flags=re.MULTILINE)
        
        if len(xaml_files) > 1:
            for i in range(1, len(xaml_files), 3):
                if i+2 <= len(xaml_files):
                    project_folder = xaml_files[i].strip()
                    relative_path_in_project = xaml_files[i+1].strip()
                    xaml_code_content = xaml_files[i+2].strip()

                    full_xaml_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': xaml_code_content, 'path': full_xaml_path, 'type': 'xaml'})

    # Manejar archivos de configuración (<config>)
    if blocks['config']:
        # Asumiendo que <config> contiene un solo archivo App.config o Web.config
        # Por simplicidad, lo guardaremos en la raíz de un proyecto común (ej. DesktopApp)
        # Idealmente, se especificaría la ruta en el AIO
        file_map.append({'content': blocks['config'][0], 'path': os.path.join("DesktopApp", "App.config"), 'type': 'config'})

    # Otros lenguajes (Rust, Go, SQL, Lua) - ahora con rutas explícitas si el .aio las tiene
    # o con una estructura más coherente para una solución VS
    if blocks['rs']:
        rs_content = blocks['rs'][0]
        # Buscar el comentario de archivo // File: vs_solution/BusinessLogic/RustCalculations/src/lib.rs
        rs_files = re.split(r'^\s*//\s*File:\s*vs_solution/([^/\\]+)/(.+\.rs)\s*$', rs_content, flags=re.MULTILINE)
        if len(rs_files) > 1:
             for i in range(1, len(rs_files), 3):
                if i+2 <= len(rs_files):
                    project_folder = rs_files[i].strip()
                    relative_path_in_project = rs_files[i+1].strip()
                    rs_code_content = rs_files[i+2].strip()
                    full_rs_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': rs_code_content, 'path': full_rs_path, 'type': 'rs'})


    if blocks['go']:
        go_content = blocks['go'][0]
        go_files = re.split(r'^\s*//\s*File:\s*vs_solution/([^/\\]+)/(.+\.go)\s*$', go_content, flags=re.MULTILINE)
        if len(go_files) > 1:
             for i in range(1, len(go_files), 3):
                if i+2 <= len(go_files):
                    project_folder = go_files[i].strip()
                    relative_path_in_project = go_files[i+1].strip()
                    go_code_content = go_files[i+2].strip()
                    full_go_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': go_code_content, 'path': full_go_path, 'type': 'go'})

    if blocks['sql']:
        sql_content = blocks['sql'][0]
        sql_files = re.split(r'^\s*--\s*File:\s*vs_solution/([^/\\]+)/(.+\.sql)\s*$', sql_content, flags=re.MULTILINE)
        if len(sql_files) > 1:
             for i in range(1, len(sql_files), 3):
                if i+2 <= len(sql_files):
                    project_folder = sql_files[i].strip()
                    relative_path_in_project = sql_files[i+1].strip()
                    sql_code_content = sql_files[i+2].strip()
                    full_sql_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': sql_code_content, 'path': full_sql_path, 'type': 'sql'})

    if blocks['lua']:
        # Asumiendo un único archivo lua de configuración global o para el proyecto API
        file_map.append({'content': blocks['lua'][0], 'path': os.path.join("ApiProject", "config.lua"), 'type': 'lua'})


    # Guardar todos los archivos definidos en file_map
    print("\n--- Guardando archivos generados ---")
    for item in file_map:
        content = item['content']
        relative_path = item['path'] # Esta es la ruta relativa al output_dir, incluyendo subdirectorios
        file_type = item['type']

        full_path = os.path.join(output_dir, relative_path)
        
        # Asegurarse de que el directorio padre exista
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                # Añadir doctype y referencias para HTML principal
                if file_type == 'html' and relative_path == 'index.html': # Solo para el index.html principal
                    f.write("<!DOCTYPE html>\n<html>\n<head>\n")
                    f.write(f"<title>{config.get('project_name', 'Aio Project')}</title>\n")
                    # Rutas relativas al output_dir para CSS y JS del frontend
                    f.write(f"<link rel='stylesheet' href='{os.path.basename(os.path.join(output_dir, 'style.css'))}'>\n")
                    f.write("</head>\n<body>\n")
                    f.write(content.strip())
                    f.write(f"\n<script src='{os.path.basename(os.path.join(output_dir, 'script.js'))}'></script>\n</body>\n</html>")
                else:
                    f.write(content.strip())
            print(f"'{full_path}' generado con éxito.")
        except Exception as e:
            print(f"Error al generar '{full_path}': {e}")
            
    # Procesa el bloque <crea> después de generar los archivos iniciales
    # Esto asegura que los comandos de borrado o creación de assets se ejecuten sobre los archivos ya generados
    if blocks['crea_block']:
        for crea_content in blocks['crea_block']:
            parse_crea_block(crea_content, output_dir)

    # Opcional: guardar el contenido bruto del meta
    if blocks['meta_block']:
        meta_output_path = os.path.join(output_dir, f'config_{base_name}.meta')
        with open(meta_output_path, 'w', encoding='utf-8') as f:
            f.write(blocks['meta_block'][0].strip())
        print(f"Configuración meta guardada en '{meta_output_path}'.")

# --- Aquí comienza la ejecución del programa ---
print("Buscando archivos .aio en el directorio actual...")
aio_files_found = [f for f in os.listdir('.') if f.endswith('.aio')]

if not aio_files_found:
    print("No se encontraron archivos .aio en el directorio actual.")
else:
    for aio_file in aio_files_found:
        base_name = os.path.splitext(aio_file)[0]
        aio_code_blocks, config = parse_aio_file(aio_file)
        
        # Validar si config tiene output_dir y si aio_code_blocks no es None
        if aio_code_blocks is None:
            print(f"Skipping {aio_file} due to parsing errors.")
            continue # Salta este archivo .aio si no se pudo parsear
        
        # Establecer el output_dir basándose en el meta del .aio, o un valor por defecto
        # (Este valor ya se obtiene en save_blocks_to_files, pero lo mantenemos aquí para claridad)
        # La verdadera creación del directorio principal ocurre en save_blocks_to_files
        
        save_blocks_to_files(aio_code_blocks, config, base_name)
    print("\nProcesamiento de todos los archivos .aio completado.")
