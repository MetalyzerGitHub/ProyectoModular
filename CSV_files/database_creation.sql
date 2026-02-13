CREATE SCHEMA `proyectomod`;
USE `proyectomod`;

CREATE TABLE usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre_usuario VARCHAR(100) NOT NULL UNIQUE,
    -- correo VARCHAR(150) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE words (
    id_word INT NOT NULL PRIMARY KEY,
    spelling VARCHAR(50) NOT NULL,
    wlen INT,
    frequency DECIMAL(5,3),
    part_of_speech VARCHAR(25),
    meaning VARCHAR(255) CHARACTER SET 'latin1' COLLATE 'latin1_spanish_ci',
    img_path VARCHAR(255)
);

-- IMPORTAR LOS DATOS DEL CSV (Table Data Import Wizard) A LA TABLA "words"
-- Intentar con la version word_data_latin1.csv si la version utf8 no funciona

CREATE TABLE juegos (
	id_juego INT AUTO_INCREMENT PRIMARY KEY,
	nombre VARCHAR(120),
	descripcion TEXT
);

CREATE TABLE intentos (
    id_intento INT AUTO_INCREMENT PRIMARY KEY,
    fk_usuario INT NOT NULL,
    fk_palabra INT NOT NULL,
    fk_juego INT NOT NULL,
    correcto BOOLEAN NOT NULL,
    tiempo INT,
    numero_intentos INT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_intentos_usuario
        FOREIGN KEY (fk_usuario) REFERENCES usuarios(id_usuario),

    CONSTRAINT fk_intentos_palabra
        FOREIGN KEY (fk_palabra) REFERENCES words(id_word),

    CONSTRAINT fk_intentos_juego
        FOREIGN KEY (fk_juego) REFERENCES juegos(id_juego)
) ENGINE=InnoDB;