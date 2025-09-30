import os
import json
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

load_dotenv()

def setup_s3_bucket():
    """Configura automáticamente el bucket S3 con todas las políticas necesarias"""
    print("🚀 Configurando bucket S3 automáticamente...")
    
    # Verificar variables de entorno
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
    
    print(f"📊 Bucket: {bucket_name}")
    print(f"📊 Región: {aws_region}")
    
    if not all([aws_access_key, aws_secret_key]):
        print("❌ Faltan credenciales de AWS")
        return False
    
    try:
        # Crear cliente S3
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        # 1. Crear bucket si no existe
        print(f"🪣 Verificando/creando bucket: {bucket_name}")
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print("✅ Bucket ya existe")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print("➕ Creando bucket...")
                if aws_region == 'us-east-1':
                    # us-east-1 no necesita LocationConstraint
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': aws_region}
                    )
                print("✅ Bucket creado")
            else:
                raise e
        
        # 2. Configurar política de bucket con permisos completos
        print("🔓 Configurando política de bucket...")
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": [
                        "s3:GetObject",
                        "s3:GetObjectVersion"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                },
                {
                    "Sid": "PublicListBucket",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:ListBucket",
                    "Resource": f"arn:aws:s3:::{bucket_name}"
                },
                {
                    "Sid": "PublicPutObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": [
                        "s3:PutObject",
                        "s3:PutObjectAcl"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                },
                {
                    "Sid": "PublicDeleteObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": [
                        "s3:DeleteObject",
                        "s3:DeleteObjectVersion"
                    ],
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        try:
            s3_client.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print("✅ Política de bucket configurada")
        except ClientError as e:
            print(f"⚠️ Error configurando política: {e}")
        
        # 3. Configurar CORS para el frontend con permisos completos
        print("🌐 Configurando CORS...")
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': [
                        'GET',      # Leer archivos
                        'PUT',      # Subir/editar archivos
                        'POST',     # Subir archivos
                        'DELETE',   # Eliminar archivos
                        'HEAD'      # Verificar existencia
                    ],
                    'AllowedOrigins': ['*'],  # Permitir todos los orígenes por ahora
                    'ExposeHeaders': [
                        'ETag',
                        'Content-Length',
                        'Content-Type',
                        'Last-Modified'
                    ],
                    'MaxAgeSeconds': 3600
                }
            ]
        }
        
        try:
            s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration=cors_configuration
            )
            print("✅ CORS configurado")
        except ClientError as e:
            print(f"⚠️ Error configurando CORS: {e}")
        
        # 4. Configurar ACL para hacer el bucket público
        print("🔓 Configurando ACL...")
        try:
            s3_client.put_bucket_acl(
                Bucket=bucket_name,
                ACL='public-read'
            )
            print("✅ ACL configurado")
        except ClientError as e:
            print(f"⚠️ Error configurando ACL: {e}")
        
        # 5. Configurar website hosting (opcional)
        print("🌐 Configurando website hosting...")
        try:
            s3_client.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': 'index.html'},
                    'ErrorDocument': {'Key': 'error.html'}
                }
            )
            print("✅ Website hosting configurado")
        except ClientError as e:
            print(f"⚠️ Error configurando website: {e}")
        
        # 6. Probar subida de archivo
        print("📤 Probando subida de archivo...")
        test_content = "Test file for HogarPerú"
        test_key = "test/hogar-peru-test.txt"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_content.encode('utf-8'),
            ContentType='text/plain',
            ACL='public-read'
        )
        
        # Generar URL pública
        public_url = f"https://{bucket_name}.s3.{aws_region}.amazonaws.com/{test_key}"
        print(f"✅ Archivo subido: {public_url}")
        
        # 7. Crear estructura de carpetas
        print("📁 Creando estructura de carpetas...")
        folders = [
            'users/profiles/',
            'properties/images/',
            'documents/invoices/',
            'temp/'
        ]
        
        for folder in folders:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=folder,
                Body=b'',
                ACL='public-read'
            )
            print(f"   ✅ Carpeta creada: {folder}")
        
        # 8. Mostrar información del bucket
        print("\n🎉 ¡Bucket configurado exitosamente!")
        print(f"📊 Bucket: {bucket_name}")
        print(f"📊 Región: {aws_region}")
        print(f"🔗 URL base: https://{bucket_name}.s3.{aws_region}.amazonaws.com/")
        print(f"🔗 URL de prueba: {public_url}")
        
        # 9. Mostrar comandos útiles
        print("\n📋 Comandos útiles:")
        print(f"   • Listar objetos: aws s3 ls s3://{bucket_name}/")
        print(f"   • Sincronizar: aws s3 sync ./local-folder s3://{bucket_name}/")
        print(f"   • Eliminar todo: aws s3 rm s3://{bucket_name}/ --recursive")
        
        return True
        
    except NoCredentialsError:
        print("❌ Error: Credenciales de AWS no encontradas")
        return False
    except ClientError as e:
        print(f"❌ Error de AWS: {e}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

def test_bucket_access():
    """Prueba el acceso al bucket configurado"""
    print("\n🧪 Probando acceso al bucket...")
    
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    bucket_name = os.getenv('S3_BUCKET_NAME', 'hogar-peru-bucket')
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        
        # Listar objetos
        response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
        
        if 'Contents' in response:
            print(f"📁 Encontrados {len(response['Contents'])} objetos:")
            for obj in response['Contents']:
                print(f"   - {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("📁 Bucket vacío")
        
        print("✅ Acceso al bucket funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Error probando acceso: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_bucket_access()
    else:
        setup_s3_bucket()