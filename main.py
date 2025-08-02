# main.py (VERSIÓN FINAL Y CORREGIDA)
import re
import os
import shutil

# Placeholder para los estados de los pines de (esp)
# En una implementación real, esto vendría de un intérprete de (esp)
esp_pin_states = {
    "n": "si", # Por defecto, 'si' para game_over
    "p": "no",  # Por defecto, 'no' para victory
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
    # Procesar línea por línea, ignorando comentarios y líneas vacías
    lines = crea_content.split('\n')
    
    print("\n--- Procesando comandos <crea> ---")
    for line in lines:
        cmd = line.strip()
        if not cmd or cmd.startswith('#'):
            continue # Ignorar líneas vacías o comentarios completos

        # Eliminar comentarios al final de la línea para el parseo del comando
        cmd_without_comment = cmd.split('#', 1)[0].strip()

        # Comando $crea=file
        create_match = re.match(r'\$crea=file\s+Name="([^"]+)"\s*(%extencion\s*\.([^,\s]+))?\s*(%Not_extencion)?(,)?', cmd_without_comment)
        if create_match:
            name = create_match.group(1)
            extension = create_match.group(3)
            not_extension_flag = create_match.group(4)

            # Reemplaza '_' por espacios en el nombre para la ruta del sistema de archivos
            file_or_dir_name_fs = name.replace('_', ' ')
            file_path = os.path.join(output_dir, file_or_dir_name_fs)
            
            if not_extension_flag:
                # Si es %Not_extencion, crear un directorio
                if not os.path.exists(file_path):
                    os.makedirs(file_path)
                    print(f"Directorio creado: '{file_path}'")
                else:
                    print(f"Directorio ya existe: '{file_path}'")
            else:
                # Crear un archivo con o sin extensión
                final_path = f"{file_path}.{extension}" if extension else file_path
                try:
                    with open(final_path, 'w', encoding='utf-8') as f:
                        f.write(f"# Archivo creado por Aio: {os.path.basename(final_path)}\n")
                    print(f"Archivo creado: '{final_path}'")
                except Exception as e:
                    print(f"Error al crear archivo '{final_path}': {e}")
            continue

        # Comando %borra
        delete_match = re.match(r'%borra=(?:Name="([^"]+)"|file="([^"]+)")(?:\s*(%all))?(?:\s*%([^,\s]+(?:,[^,\s]+)*))?(?:\s*&con\s*"([^"]+)")?(,)?', cmd_without_comment)
        if delete_match:
            name_to_delete = delete_match.group(1)
            path_to_delete = delete_match.group(2)
            all_flag = delete_match.group(3)
            specific_files_str = delete_match.group(4)
            conditional_logic = delete_match.group(5)

            target_path_base = ""
            if name_to_delete:
                target_path_base = os.path.join(output_dir, name_to_delete.replace('_', ' '))
            elif path_to_delete:
                target_path_base = os.path.join(output_dir, path_to_delete.replace('_', ' '))
            else:
                print(f"Error: Comando %borra incompleto (falta Name o file): {cmd}")
                continue
            
            # Evaluar la condición &con
            condition_met = True
            if conditional_logic:
                pin_name = conditional_logic.strip('"')
                # Simulamos la condición. En un intérprete real, esto vendría de la ejecución de (esp)
                if pin_name in esp_pin_states:
                    # La condición para borrar se cumple si el pin NO es "no"
                    # Si el pin_name es 'n' (game_over) y está en 'si', significa game over, así que no se borra.
                    # Si el pin_name es 'p' (victory) y está en 'no', significa no victory, así que no se borra.
                    # El user quiere borrar si el pin 'n' es 'no', o si 'p' es 'si' (asumiendo su ejemplo)
                    # En la lógica original del usuario:
                    # %borra=file="build/script.js" &con "n", # se borra si 'n' es 'no' (significa no game_over)
                    # %borra=file="build/patterns_mi_buscaminas.pat" &con "p", # se borra si 'p' es 'si' (significa victory)

                    # Ajustando la lógica de la condición aquí basada en el ejemplo del usuario
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
                    # Construir la ruta completa al archivo específico
                    file_to_delete_path = os.path.join(target_path_base, f_name.replace('_', ' '))

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
        return None, {} # Devuelve None para bloques y un diccionario vacío para config
    except Exception as e:
        print(f"Error al leer el archivo '{file_path}': {e}")
        return None, {}

    # Obtener configuración del bloque <meta>
    config = parse_meta_block(content)

    # Patrones para encontrar los bloques de código con expresiones regulares
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

# Esta función guardará cada bloque en un archivo separado
def save_blocks_to_files(blocks, config, base_name):
    output_dir = config.get('output_dir', '.')

    if not os.path.exists(output_dir) and output_dir != '.':
        os.makedirs(output_dir)
        print(f"Directorio de salida '{output_dir}/' creado.")

    files_to_create = []

    # Bloques web
    if blocks['html']:
        files_to_create.append((blocks['html'][0], 'index', '.html'))
    if blocks['css']:
        files_to_create.append((blocks['css'][0], 'style', '.css'))
    if blocks['js']:
        files_to_create.append((blocks['js'][0], 'script', '.js'))

    # Bloques de lógica DSL
    if blocks['esp']:
        files_to_create.append((blocks['esp'][0], f'logic_{base_name}', '.esp'))
    if blocks['ing']:
        files_to_create.append((blocks['ing'][0], f'logic_{base_name}', '.ing'))
    if blocks['pat']:
        files_to_create.append((blocks['pat'][0], f'patterns_{base_name}', '.pat'))

    # Bloques de otros lenguajes
    if blocks['net']:
        files_to_create.append((blocks['net'][0], f'Program_{base_name}', '.cs'))
    if blocks['lua']:
        files_to_create.append((blocks['lua'][0], f'main_{base_name}', '.lua'))
    if blocks['rs']:
        files_to_create.append((blocks['rs'][0], f'src/main_{base_name}', '.rs'))
    if blocks['go']:
        files_to_create.append((blocks['go'][0], f'main_{base_name}', '.go'))
    if blocks['sql']:
        files_to_create.append((blocks['sql'][0], f'schema_{base_name}', '.sql'))

    # Nuevos bloques .NET/configuración
    if blocks['sln']:
        files_to_create.append((blocks['sln'][0], f'{base_name}', '.sln'))
    if blocks['xaml']:
        files_to_create.append((blocks['xaml'][0], f'MainPage', '.xaml'))
    if blocks['config']:
        files_to_create.append((blocks['config'][0], f'App', '.config'))
    if blocks['csproj']:
        files_to_create.append((blocks['csproj'][0], f'{base_name}', '.csproj'))

    for content, name, ext in files_to_create:
        if ext == '.rs': # Manejo especial para Rust (va en src/)
            file_dir = os.path.join(output_dir, os.path.dirname(name))
            file_name = os.path.basename(name)
            if not os.path.exists(file_dir):
                os.makedirs(file_dir)
            full_path = os.path.join(file_dir, f'{file_name}{ext}')
        else:
            full_path = os.path.join(output_dir, f'{name}{ext}')

        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                if ext == '.html':
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
        # Solo procede si aio_code_blocks no es None (es decir, el archivo .aio se encontró y parseó)
        if aio_code_blocks:
            save_blocks_to_files(aio_code_blocks, config, base_name)
    print("\nProcesamiento de todos los archivos .aio completado.")
