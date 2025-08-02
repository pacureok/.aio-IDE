import re
import os
import shutil
import xml.etree.ElementTree as ET # Para parsear XML de CSPROJ

# Placeholder para los estados de los pines de (esp)
esp_pin_states = {
    "deploy_success": "no",
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

            # Reemplaza '_' por '/' en el nombre para la ruta del sistema de archivos
            file_or_dir_path_relative = name.replace('_', os.sep)
            full_path_target = os.path.join(output_dir, file_or_dir_path_relative)
            
            if not_extension_flag:
                # Si es %Not_extencion, crear un directorio
                if not os.path.exists(full_path_target):
                    os.makedirs(full_path_target)
                    print(f"Directorio creado: '{full_path_target}'")
                else:
                    print(f"Directorio ya existe: '{full_path_target}' (ignorado)")
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
            path_to_delete_relative = delete_match.group(2)
            all_flag = delete_match.group(3)
            specific_files_str = delete_match.group(4)
            conditional_logic_pin_name = delete_match.group(5)

            target_path_base = ""
            if name_to_delete:
                target_path_base = os.path.join(output_dir, name_to_delete.replace('_', os.sep))
            elif path_to_delete_relative:
                target_path_base = path_to_delete_relative
                if not os.path.isabs(target_path_base):
                    target_path_base = os.path.join(output_dir, target_path_base)
            else:
                print(f"Error: Comando %borra incompleto (falta Name o file): {cmd}")
                continue
            
            condition_met = True
            if conditional_logic_pin_name:
                pin_name = conditional_logic_pin_name.strip('"')
                if pin_name in esp_pin_states:
                    if pin_name == "deploy_success":
                        if esp_pin_states[pin_name] == "no":
                            condition_met = False
                            print(f"Condición '{pin_name}' no se cumple (estado '{esp_pin_states[pin_name]}'). Borrado no ejecutado para '{target_path_base}'.")
                    else:
                        if (pin_name == "n" and esp_pin_states[pin_name] == "si") or \
                           (pin_name == "p" and esp_pin_states[pin_name] == "no"):
                            condition_met = False
                            print(f"Condición '{pin_name}' no se cumple (estado '{esp_pin_states[pin_name]}'). Borrado no ejecutado para '{target_path_base}'.")
                else:
                    print(f"Advertencia: Pin '{pin_name}' no encontrado en estados de (esp). No se puede evaluar condición. Asumiendo TRUE.")
            
            if not condition_met:
                continue

            if all_flag:
                if os.path.exists(target_path_base):
                    if os.path.isdir(target_path_base):
                        shutil.rmtree(target_path_base)
                        print(f"Directorio y contenido borrados: '{target_path_base}'")
                    else:
                        os.remove(target_path_base)
                        print(f"Archivo borrado: '{target_path_base}'")
                else:
                    print(f"Advertencia: '{target_path_base}' no encontrado para borrado %all.")
            elif specific_files_str:
                files_to_delete = [f.strip() for f in specific_files_str.split(',')]
                for f_name in files_to_delete:
                    file_to_delete_path = os.path.join(os.path.dirname(target_path_base), f_name.replace('_', os.sep))
                    if os.path.exists(file_to_delete_path) and os.path.isfile(file_to_delete_path):
                        os.remove(file_to_delete_path)
                        print(f"Archivo borrado: '{file_to_delete_path}'")
                    else:
                        print(f"Advertencia: '{file_to_delete_path}' no encontrado o no es un archivo para borrado.")
            elif name_to_delete:
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
        # Asumiendo que el nombre de la solución es el base_name del archivo .aio
        file_map.append({'content': blocks['sln'][0], 'path': f'{base_name}.sln', 'type': 'sln'})

    # .NET Projects and associated files (C#, XAML, Config, CSPROJ)
    
    # Manejo de CSPROJ: Tu bloque <csproj> en el .aio contiene MÚLTIPLES <Project ...>
    if blocks['csproj']:
        full_csproj_content = "\n".join(blocks['csproj'])
        
        csproj_project_matches = re.finditer(r'<Project Sdk="([^"]+)">\s*(.*?)</Project>', full_csproj_content, re.DOTALL)
        
        for i, match in enumerate(csproj_project_matches):
            sdk_type = match.group(1) 
            project_xml_content = match.group(0) 

            try:
                root = ET.fromstring(project_xml_content)
                project_name = None
                
                for prop_group in root.findall('.//PropertyGroup'):
                    root_ns = prop_group.find('RootNamespace')
                    if root_ns is not None and root_ns.text:
                        project_name = root_ns.text.strip()
                        break
                    assembly_name = prop_group.find('AssemblyName')
                    if assembly_name is not None and assembly_name.text:
                        project_name = assembly_name.text.strip()
                        break
                
                if not project_name:
                    output_type_elem = root.find('.//OutputType')
                    if output_type_elem is not None and output_type_elem.text:
                        if "WinExe" in output_type_elem.text or "Exe" in output_type_elem.text:
                            project_name = "DesktopApp" if "WinExe" in output_type_elem.text else "ConsoleApp"
                        elif "Library" in output_type_elem.text:
                            project_name = "BusinessLogic"
                    
                if not project_name:
                    project_name = f'UnnamedProject_{i}'
                    if "Web" in sdk_type:
                        project_name = "ApiProject"
                    elif "Test" in sdk_type:
                        project_name = "TestsProject"
                    elif i == 2: # Tercer csproj en tu .aio es BusinessLogic
                        project_name = "BusinessLogic"
                        
            except ET.ParseError as e:
                print(f"Advertencia: Error al parsear CSPROJ XML para el proyecto {i}: {e}. Usando nombre genérico.")
                project_name = f'UnnamedProject_{i}'
            
            csproj_filename = f"{project_name}.csproj"
            project_folder = project_name 

            csproj_path = os.path.join(project_folder, csproj_filename)
            file_map.append({'content': project_xml_content, 'path': csproj_path, 'type': 'csproj'})
            print(f"CSPROJ: '{csproj_path}' identificado y preparado para guardar.")


    # Manejar archivos C# (<net>) - Usa el mismo split por comentario 'File:'
    for net_content in blocks.get('net', []):
        cs_files = re.split(r'^\s*//\s*File:\s*([^/\\]+)/(.+\.cs)\s*$', net_content, flags=re.MULTILINE)
        if len(cs_files) > 1:
            for i in range(1, len(cs_files), 3):
                if i + 2 < len(cs_files):
                    project_folder = cs_files[i].strip()
                    relative_path_in_project = cs_files[i+1].strip()
                    cs_code_content = cs_files[i+2].strip()

                    full_cs_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': cs_code_content, 'path': full_cs_path, 'type': 'cs'})
                    print(f"C#: '{full_cs_path}' identificado y preparado para guardar.")
                else:
                    print(f"Advertencia: Bloque <net> split incompleto. Ignorando parte.")


    # Manejar archivos XAML (<xaml>) - Guardar como un archivo fijo, ya que no tiene comentarios File: en tu .aio
    if blocks['xaml']:
        file_map.append({'content': blocks['xaml'][0], 'path': os.path.join("DesktopApp", "MainWindow.xaml"), 'type': 'xaml'})
        print(f"XAML: 'DesktopApp/MainWindow.xaml' identificado y preparado para guardar.")


    # Manejar archivos de configuración (<config>) - Guardar como un archivo fijo
    if blocks['config']:
        file_map.append({'content': blocks['config'][0], 'path': os.path.join("DesktopApp", "App.config"), 'type': 'config'})
        print(f"CONFIG: 'DesktopApp/App.config' identificado y preparado para guardar.")

    # Otros lenguajes (Rust, Go, SQL, Lua) - Usa el split por comentario 'File:'
    if blocks['rs']:
        rs_content = blocks['rs'][0]
        rs_files = re.split(r'^\s*//\s*File:\s*([^/\\]+)/(.+\.rs)\s*$', rs_content, flags=re.MULTILINE)
        if len(rs_files) > 1:
            for i in range(1, len(rs_files), 3):
                if i+2 < len(rs_files):
                    project_folder = rs_files[i].strip()
                    relative_path_in_project = rs_files[i+1].strip()
                    rs_code_content = rs_files[i+2].strip()
                    full_rs_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': rs_code_content, 'path': full_rs_path, 'type': 'rs'})
                    print(f"Rust: '{full_rs_path}' identificado y preparado para guardar.")
                else:
                    print(f"Advertencia: Bloque <rs> split incompleto. Ignorando parte.")
        else:
             file_map.append({'content': blocks['rs'][0], 'path': os.path.join("BusinessLogic", "RustCalculations", "src", "lib.rs"), 'type': 'rs'})
             print(f"Rust (default): 'BusinessLogic/RustCalculations/src/lib.rs' identificado y preparado para guardar.")


    if blocks['go']:
        go_content = blocks['go'][0]
        go_files = re.split(r'^\s*//\s*File:\s*([^/\\]+)/(.+\.go)\s*$', go_content, flags=re.MULTILINE)
        if len(go_files) > 1:
            for i in range(1, len(go_files), 3):
                if i+2 < len(go_files):
                    project_folder = go_files[i].strip()
                    relative_path_in_project = go_files[i+1].strip()
                    go_code_content = go_files[i+2].strip()
                    full_go_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': go_code_content, 'path': full_go_path, 'type': 'go'})
                    print(f"Go: '{full_go_path}' identificado y preparado para guardar.")
                else:
                    print(f"Advertencia: Bloque <go> split incompleto. Ignorando parte.")
        else: 
            file_map.append({'content': blocks['go'][0], 'path': os.path.join("ApiProject", "GoLogger", "main.go"), 'type': 'go'})
            print(f"Go (default): 'ApiProject/GoLogger/main.go' identificado y preparado para guardar.")


    if blocks['sql']:
        sql_content = blocks['sql'][0]
        sql_files = re.split(r'^\s*--\s*File:\s*([^/\\]+)/(.+\.sql)\s*$', sql_content, flags=re.MULTILINE)
        if len(sql_files) > 1:
            for i in range(1, len(sql_files), 3):
                if i+2 < len(sql_files):
                    project_folder = sql_files[i].strip()
                    relative_path_in_project = sql_files[i+1].strip()
                    sql_code_content = sql_files[i+2].strip()
                    full_sql_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': sql_code_content, 'path': full_sql_path, 'type': 'sql'})
                    print(f"SQL: '{full_sql_path}' identificado y preparado para guardar.")
                else:
                    print(f"Advertencia: Bloque <sql> split incompleto. Ignorando parte.")
        else: 
            file_map.append({'content': blocks['sql'][0], 'path': os.path.join("SqlDatabase", "Migrations", "001_InitialSchema.sql"), 'type': 'sql'})
            print(f"SQL (default): 'SqlDatabase/Migrations/001_InitialSchema.sql' identificado y preparado para guardar.")


    if blocks['lua']:
        lua_content = blocks['lua'][0]
        lua_files = re.split(r'^\s*--\s*File:\s*([^/\\]+)/(.+\.lua)\s*$', lua_content, flags=re.MULTILINE)
        if len(lua_files) > 1:
            for i in range(1, len(lua_files), 3):
                if i+2 < len(lua_files):
                    project_folder = lua_files[i].strip()
                    relative_path_in_project = lua_files[i+1].strip()
                    lua_code_content = lua_files[i+2].strip()
                    full_lua_path = os.path.join(project_folder, relative_path_in_project)
                    file_map.append({'content': lua_code_content, 'path': full_lua_path, 'type': 'lua'})
                    print(f"Lua: '{full_lua_path}' identificado y preparado para guardar.")
                else:
                    print(f"Advertencia: Bloque <lua> split incompleto. Ignorando parte.")
        else: 
            file_map.append({'content': blocks['lua'][0], 'path': os.path.join("ApiProject", "config.lua"), 'type': 'lua'})
            print(f"Lua (default): 'ApiProject/config.lua' identificado y preparado para guardar.")


    # Guardar todos los archivos definidos en file_map
    print("\n--- Guardando archivos generados ---")
    for item in file_map:
        content = item['content']
        relative_path = item['path'] 
        file_type = item['type']

        full_path = os.path.join(output_dir, relative_path)
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                if file_type == 'html' and relative_path == 'index.html':
                    f.write("<!DOCTYPE html>\n<html>\n<head>\n")
                    f.write(f"<title>{config.get('project_name', 'Aio Project')}</title>\n")
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
    if blocks['crea_block']:
        for crea_content in blocks['crea_block']:
            parse_crea_block(crea_content, output_dir)

    # Opcional: guardar el contenido bruto del meta
    if blocks['meta_block']:
        meta_output_path = os.path.join(output_dir, f'config_{base_name}.meta')
        os.makedirs(os.path.dirname(meta_output_path), exist_ok=True)
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
        
        if aio_code_blocks is None:
            print(f"Saltando {aio_file} debido a errores de parseo.")
            continue
        
        save_blocks_to_files(aio_code_blocks, config, base_name)
    print("\nProcesamiento de todos los archivos .aio completado.")
