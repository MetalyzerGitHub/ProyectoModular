CREATE SCHEMA `proyectomod`;
USE `proyectomod`;

CREATE TABLE usuarios (
    id_usuario INT AUTO_INCREMENT PRIMARY KEY,
    nombre_usuario VARCHAR(100) NOT NULL UNIQUE,
    -- correo VARCHAR(150) NOT NULL UNIQUE,
    contrasena_hash VARCHAR(255) NOT NULL,
    nivel DECIMAL(5, 2) DEFAULT '0',
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

INSERT INTO juegos (nombre, descripcion)
VALUES 
('Hangman', 'Escoge las letras correctas. '),
('Match', 'Relaciona las palabras correctamente. '),
('Quiz', 'Selecciona la palabra correcta. '),
('Word Unscramble', 'Reordena la palabra. ');

ALTER TABLE words ADD difficulty DECIMAL(4,3) DEFAULT 0.500;
-- Normalizar frecuencia y longitud, luego calcular dificultad
SET @min_freq = (SELECT MIN(frequency) FROM words);
SET @max_freq = (SELECT MAX(frequency) FROM words);
SET @min_len  = (SELECT MIN(wlen) FROM words);
SET @max_len  = (SELECT MAX(wlen) FROM words);

UPDATE words -- desactivar safe mode para ejecutar
SET difficulty = (
    (1.0 - (frequency - @min_freq) / NULLIF(@max_freq - @min_freq, 0)) 
    + 
    (wlen - @min_len) / NULLIF(@max_len - @min_len, 0)
) / 2;
ALTER TABLE usuarios ADD skill DECIMAL(4,3) DEFAULT 0.500;
    