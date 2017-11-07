import os  # true random
import sys

def generate_secret(secret_name):
    """
    Secret generator for Linboot
    Outputs two files:
        binary file *.bin with 256-key and 128-IVC to encrypt firmware before release
        include file *.inc with 256-key and 128-IVC to build Linboot bootloader
    :param secret_name: output filename
    :return:
    """
    secret = os.urandom(256//8+128//8)
    with open(secret_name + ".bin", "wb") as secret_binfile:
        secret_binfile.write(secret)
    sys.stdout.write('[INFO   ] Создан ключ {0}\n'.format(secret_name + ".bin"))
    with open(secret_name + ".inc", "w") as secret_inc:
        secret = iter(secret)
        secret_inc.write("#include <avr/pgmspace.h>\n\n"
                         "const unsigned char key[] = {\n")
        for i in range(4):
            secret_inc.write("\t")
            for j in range(8):
                secret_inc.write(hex(next(secret)))
                if j != 7:
                    secret_inc.write(", ")
                elif i != 3:
                    secret_inc.write(",\n")
                else:
                    secret_inc.write("\n")
        secret_inc.write("};\n\nconst unsigned char iv[] PROGMEM = {\n")
        for i in range(2):
            secret_inc.write("\t")
            for j in range(8):
                secret_inc.write(hex(next(secret)))
                if j != 7:
                    secret_inc.write(", ")
                elif i != 1:
                    secret_inc.write(",\n")
                else:
                    secret_inc.write("\n")
        secret_inc.write("};\n")
    sys.stdout.write('[INFO   ] Создан заголовочный файл {0}\n'.format(secret_name + ".inc"))
    sys.stdout.write("[INFO   ] Готово\n")
