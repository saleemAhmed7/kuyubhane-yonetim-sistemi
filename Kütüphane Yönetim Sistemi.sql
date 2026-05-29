-- ============================================================================
-- ÜNİVERSİTE KÜTÜPHANE YÖNETİM SİSTEMİ (kutuphane_yonetim_sistemi)
-- VERİTABANI TASARIMI VE OLUŞTURMA BETİĞİ (MySQL)
-- ============================================================================

-- Veritabanının oluşturulması ve seçilmesi
DROP DATABASE IF EXISTS kutuphane_yonetim_sistemi;
CREATE DATABASE kutuphane_yonetim_sistemi
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE kutuphane_yonetim_sistemi;

-- ============================================================================
-- 1. TABLOLARIN OLUŞTURULMASI
-- ============================================================================

-- A. Ogrenciler Tablosu
CREATE TABLE Ogrenciler (
    OgrenciID INT AUTO_INCREMENT PRIMARY KEY,
    AdSoyad VARCHAR(150) NOT NULL,
    OgrenciNo VARCHAR(50) NOT NULL UNIQUE,
    Bolum VARCHAR(100) NOT NULL,
    Telefon VARCHAR(20),
    Eposta VARCHAR(100) NOT NULL UNIQUE,
    KayitTarihi DATE NOT NULL DEFAULT (CURDATE()),
    CONSTRAINT chk_ogrenci_eposta CHECK (Eposta LIKE '%@%.%')
) ENGINE=InnoDB;

-- B. Kitaplar Tablosu
CREATE TABLE Kitaplar (
    KitapID INT AUTO_INCREMENT PRIMARY KEY,
    KitapAdi VARCHAR(255) NOT NULL,
    Yazar VARCHAR(150) NOT NULL,
    Yayinevi VARCHAR(150) NOT NULL,
    YayinYili INT NOT NULL,
    ISBN VARCHAR(20) NOT NULL UNIQUE,
    ToplamKopya INT NOT NULL DEFAULT 1,
    MevcutKopya INT NOT NULL DEFAULT 1,
    CONSTRAINT chk_yayin_yili CHECK (YayinYili > 0),
    CONSTRAINT chk_toplam_kopya CHECK (ToplamKopya >= 0),
    CONSTRAINT chk_mevcut_kopya CHECK (MevcutKopya >= 0 AND MevcutKopya <= ToplamKopya)
) ENGINE=InnoDB;

-- C. KutuphaneGorevlileri Tablosu
CREATE TABLE KutuphaneGorevlileri (
    GorevliID INT AUTO_INCREMENT PRIMARY KEY,
    AdSoyad VARCHAR(150) NOT NULL,
    Telefon VARCHAR(20),
    Eposta VARCHAR(100) NOT NULL,
    KullaniciAdi VARCHAR(50) NOT NULL UNIQUE,
    Sifre VARCHAR(255) NOT NULL,
    CONSTRAINT chk_gorevli_eposta CHECK (Eposta LIKE '%@%.%')
) ENGINE=InnoDB;

-- D. OduncIslemleri Tablosu
CREATE TABLE OduncIslemleri (
    OduncID INT AUTO_INCREMENT PRIMARY KEY,
    OgrenciID INT NOT NULL,
    KitapID INT NOT NULL,
    GorevliID INT NOT NULL,
    OduncTarihi DATE NOT NULL DEFAULT (CURDATE()),
    SonTeslimTarihi DATE NOT NULL,
    IadeTarihi DATE NULL,
    Durum VARCHAR(50) NOT NULL DEFAULT 'Ödünç Verildi',
    FOREIGN KEY (OgrenciID) REFERENCES Ogrenciler(OgrenciID) ON DELETE CASCADE,
    FOREIGN KEY (KitapID) REFERENCES Kitaplar(KitapID) ON DELETE CASCADE,
    FOREIGN KEY (GorevliID) REFERENCES KutuphaneGorevlileri(GorevliID) ON DELETE CASCADE,
    CONSTRAINT chk_teslim_tarihi CHECK (SonTeslimTarihi >= OduncTarihi),
    CONSTRAINT chk_iade_tarihi CHECK (IadeTarihi IS NULL OR IadeTarihi >= OduncTarihi),
    CONSTRAINT chk_durum CHECK (Durum IN ('Ödünç Verildi', 'İade Edildi', 'Gecikmiş'))
) ENGINE=InnoDB;

-- E. Cezalar Tablosu
CREATE TABLE Cezalar (
    CezaID INT AUTO_INCREMENT PRIMARY KEY,
    OgrenciID INT NOT NULL,
    OduncID INT NOT NULL,
    CezaTutari DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    Aciklama TEXT,
    CezaTarihi DATE NOT NULL DEFAULT (CURDATE()),
    OdendiMi BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (OgrenciID) REFERENCES Ogrenciler(OgrenciID) ON DELETE CASCADE,
    FOREIGN KEY (OduncID) REFERENCES OduncIslemleri(OduncID) ON DELETE CASCADE,
    CONSTRAINT chk_ceza_tutari CHECK (CezaTutari >= 0.00)
) ENGINE=InnoDB;


-- ============================================================================
-- 2. VERİTABANI FONKSİYONLARI (FUNCTIONS)
-- ============================================================================

DELIMITER $$

-- F1. FN_CezaHesapla
-- Geciken gün sayısına göre ceza miktarını hesaplar (Günlük 5.00 TL)
CREATE FUNCTION FN_CezaHesapla(
    p_GecikmeGunu INT
)
RETURNS DECIMAL(10, 2)
DETERMINISTIC
BEGIN
    DECLARE v_Ceza DECIMAL(10, 2) DEFAULT 0.00;
    IF p_GecikmeGunu > 0 THEN
        SET v_Ceza = p_GecikmeGunu * 5.00;
    END IF;
    RETURN v_Ceza;
END $$

-- F2. FN_OgrenciAktifOduncSayisi
-- Bir öğrencinin şu anda teslim etmediği (aktif) ödünç kitap sayısını döndürür
CREATE FUNCTION FN_OgrenciAktifOduncSayisi(
    p_OgrenciID INT
)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_AktifAdet INT DEFAULT 0;
    SELECT COUNT(*) INTO v_AktifAdet
    FROM OduncIslemleri
    WHERE OgrenciID = p_OgrenciID AND IadeTarihi IS NULL;
    RETURN v_AktifAdet;
END $$

DELIMITER ;


-- ============================================================================
-- 3. VERİTABANI TETİKLEYİCİLERİ (TRIGGERS)
-- ============================================================================

DELIMITER $$

-- T1. TRG_KitapOduncKontrol (BEFORE INSERT)
-- Ödünç alma işlemi öncesinde kitabın mevcut olup olmadığını kontrol eder. Yoksa işlemi durdurur.
CREATE TRIGGER TRG_KitapOduncKontrol
BEFORE INSERT ON OduncIslemleri
FOR EACH ROW
BEGIN
    DECLARE v_Mevcut INT;
    SELECT MevcutKopya INTO v_Mevcut
    FROM Kitaplar
    WHERE KitapID = NEW.KitapID;
    
    IF v_Mevcut < 1 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Hata: Seçilen kitaba ait kütüphanede mevcut kopya bulunmamaktadır!';
    END IF;
END $$

-- T2. TRG_KitapOduncVer (AFTER INSERT)
-- Yeni bir ödünç kaydı açıldığında Kitaplar tablosundaki MevcutKopya sayısını 1 azaltır.
CREATE TRIGGER TRG_KitapOduncVer
AFTER INSERT ON OduncIslemleri
FOR EACH ROW
BEGIN
    UPDATE Kitaplar
    SET MevcutKopya = MevcutKopya - 1
    WHERE KitapID = NEW.KitapID;
END $$

-- T3. TRG_KitapIadeEt (AFTER UPDATE)
-- Kitap iade edildiğinde (IadeTarihi NULL'dan bir tarihe güncellendiğinde) mevcut kopyayı 1 artırır,
-- ve eğer iade tarihi son teslim tarihini geçmişse otomatik olarak ceza kaydı oluşturur.
CREATE TRIGGER TRG_KitapIadeEt
AFTER UPDATE ON OduncIslemleri
FOR EACH ROW
BEGIN
    DECLARE v_GecikmeGunu INT DEFAULT 0;
    DECLARE v_Ceza DECIMAL(10, 2) DEFAULT 0.00;
    
    -- Yalnızca IadeTarihi güncellendiğinde tetiklenir
    IF OLD.IadeTarihi IS NULL AND NEW.IadeTarihi IS NOT NULL THEN
        -- 1. Kitabın mevcut kopyasını 1 arttır
        UPDATE Kitaplar
        SET MevcutKopya = MevcutKopya + 1
        WHERE KitapID = NEW.KitapID;
        
        -- 2. Gecikme kontrolü ve ceza işlemi
        IF NEW.IadeTarihi > NEW.SonTeslimTarihi THEN
            SET v_GecikmeGunu = DATEDIFF(NEW.IadeTarihi, NEW.SonTeslimTarihi);
            SET v_Ceza = FN_CezaHesapla(v_GecikmeGunu);
            
            -- Otomatik ceza kaydı oluştur
            INSERT INTO Cezalar (OgrenciID, OduncID, CezaTutari, Aciklama, CezaTarihi, OdendiMi)
            VALUES (
                NEW.OgrenciID,
                NEW.OduncID,
                v_Ceza,
                CONCAT('Gecikme Süresi: ', v_GecikmeGunu, ' gün. Günlük ceza ücreti: 5.00 TL.'),
                NEW.IadeTarihi,
                FALSE
            );
        END IF;
    END IF;
END $$

DELIMITER ;


-- ============================================================================
-- 4. SAKLI YORDAMLAR (STORED PROCEDURES)
-- ============================================================================

DELIMITER $$

-- ----------------------------------------------------------------------------
-- A. Ogrenciler Tablosu CRUD Yordamları
-- ----------------------------------------------------------------------------

-- A1. Ogrenci Ekleme
CREATE PROCEDURE sp_OgrenciEkle(
    IN p_AdSoyad VARCHAR(150),
    IN p_OgrenciNo VARCHAR(50),
    IN p_Bolum VARCHAR(100),
    IN p_Telefon VARCHAR(20),
    IN p_Eposta VARCHAR(100),
    IN p_KayitTarihi DATE
)
BEGIN
    INSERT INTO Ogrenciler (AdSoyad, OgrenciNo, Bolum, Telefon, Eposta, KayitTarihi)
    VALUES (p_AdSoyad, p_OgrenciNo, p_Bolum, p_Telefon, p_Eposta, COALESCE(p_KayitTarihi, CURDATE()));
END $$

-- A2. Ogrenci Güncelleme
CREATE PROCEDURE sp_OgrenciGuncelle(
    IN p_OgrenciID INT,
    IN p_AdSoyad VARCHAR(150),
    IN p_OgrenciNo VARCHAR(50),
    IN p_Bolum VARCHAR(100),
    IN p_Telefon VARCHAR(20),
    IN p_Eposta VARCHAR(100),
    IN p_KayitTarihi DATE
)
BEGIN
    UPDATE Ogrenciler
    SET AdSoyad = p_AdSoyad,
        OgrenciNo = p_OgrenciNo,
        Bolum = p_Bolum,
        Telefon = p_Telefon,
        Eposta = p_Eposta,
        KayitTarihi = p_KayitTarihi
    WHERE OgrenciID = p_OgrenciID;
END $$

-- A3. Ogrenci Silme
CREATE PROCEDURE sp_OgrenciSil(
    IN p_OgrenciID INT
)
BEGIN
    DELETE FROM Ogrenciler WHERE OgrenciID = p_OgrenciID;
END $$

-- A4. Öğrenci Listeleme
CREATE PROCEDURE sp_OgrenciListele()
BEGIN
    SELECT OgrenciID, AdSoyad, OgrenciNo, Bolum, Telefon, Eposta, KayitTarihi FROM Ogrenciler;
END $$

-- ----------------------------------------------------------------------------
-- B. Kitaplar Tablosu CRUD Yordamları
-- ----------------------------------------------------------------------------

-- B1. Kitap Ekleme
CREATE PROCEDURE sp_KitapEkle(
    IN p_KitapAdi VARCHAR(255),
    IN p_Yazar VARCHAR(150),
    IN p_Yayinevi VARCHAR(150),
    IN p_YayinYili INT,
    IN p_ISBN VARCHAR(20),
    IN p_ToplamKopya INT,
    IN p_MevcutKopya INT
)
BEGIN
    INSERT INTO Kitaplar (KitapAdi, Yazar, Yayinevi, YayinYili, ISBN, ToplamKopya, MevcutKopya)
    VALUES (p_KitapAdi, p_Yazar, p_Yayinevi, p_YayinYili, p_ISBN, p_ToplamKopya, p_MevcutKopya);
END $$

-- B2. Kitap Güncelleme
CREATE PROCEDURE sp_KitapGuncelle(
    IN p_KitapID INT,
    IN p_KitapAdi VARCHAR(255),
    IN p_Yazar VARCHAR(150),
    IN p_Yayinevi VARCHAR(150),
    IN p_YayinYili INT,
    IN p_ISBN VARCHAR(20),
    IN p_ToplamKopya INT,
    IN p_MevcutKopya INT
)
BEGIN
    UPDATE Kitaplar
    SET KitapAdi = p_KitapAdi,
        Yazar = p_Yazar,
        Yayinevi = p_Yayinevi,
        YayinYili = p_YayinYili,
        ISBN = p_ISBN,
        ToplamKopya = p_ToplamKopya,
        MevcutKopya = p_MevcutKopya
    WHERE KitapID = p_KitapID;
END $$

-- B3. Kitap Silme
CREATE PROCEDURE sp_KitapSil(
    IN p_KitapID INT
)
BEGIN
    DELETE FROM Kitaplar WHERE KitapID = p_KitapID;
END $$

-- B4. Kitap Listeleme
CREATE PROCEDURE sp_KitapListele()
BEGIN
    SELECT KitapID, KitapAdi, Yazar, Yayinevi, YayinYili, ISBN, ToplamKopya, MevcutKopya FROM Kitaplar;
END $$

-- ----------------------------------------------------------------------------
-- C. KutuphaneGorevlileri Tablosu CRUD Yordamları
-- ----------------------------------------------------------------------------

-- C1. Görevli Ekleme
CREATE PROCEDURE sp_GorevliEkle(
    IN p_AdSoyad VARCHAR(150),
    IN p_Telefon VARCHAR(20),
    IN p_Eposta VARCHAR(100),
    IN p_KullaniciAdi VARCHAR(50),
    IN p_Sifre VARCHAR(255)
)
BEGIN
    INSERT INTO KutuphaneGorevlileri (AdSoyad, Telefon, Eposta, KullaniciAdi, Sifre)
    VALUES (p_AdSoyad, p_Telefon, p_Eposta, p_KullaniciAdi, p_Sifre);
END $$

-- C2. Görevli Güncelleme
CREATE PROCEDURE sp_GorevliGuncelle(
    IN p_GorevliID INT,
    IN p_AdSoyad VARCHAR(150),
    IN p_Telefon VARCHAR(20),
    IN p_Eposta VARCHAR(100),
    IN p_KullaniciAdi VARCHAR(50),
    IN p_Sifre VARCHAR(255)
)
BEGIN
    UPDATE KutuphaneGorevlileri
    SET AdSoyad = p_AdSoyad,
        Telefon = p_Telefon,
        Eposta = p_Eposta,
        KullaniciAdi = p_KullaniciAdi,
        Sifre = p_Sifre
    WHERE GorevliID = p_GorevliID;
END $$

-- C3. Görevli Silme
CREATE PROCEDURE sp_GorevliSil(
    IN p_GorevliID INT
)
BEGIN
    DELETE FROM KutuphaneGorevlileri WHERE GorevliID = p_GorevliID;
END $$

-- C4. Görevli Listeleme
CREATE PROCEDURE sp_GorevliListele()
BEGIN
    SELECT GorevliID, AdSoyad, Telefon, Eposta, KullaniciAdi FROM KutuphaneGorevlileri;
END $$

-- ----------------------------------------------------------------------------
-- D. OduncIslemleri Tablosu CRUD Yordamları
-- ----------------------------------------------------------------------------

-- D1. Ödünç Ekleme
CREATE PROCEDURE sp_OduncEkle(
    IN p_OgrenciID INT,
    IN p_KitapID INT,
    IN p_GorevliID INT,
    IN p_OduncTarihi DATE,
    IN p_SonTeslimTarihi DATE
)
BEGIN
    INSERT INTO OduncIslemleri (OgrenciID, KitapID, GorevliID, OduncTarihi, SonTeslimTarihi, IadeTarihi, Durum)
    VALUES (p_OgrenciID, p_KitapID, p_GorevliID, COALESCE(p_OduncTarihi, CURDATE()), p_SonTeslimTarihi, NULL, 'Ödünç Verildi');
END $$

-- D2. Ödünç Güncelleme
CREATE PROCEDURE sp_OduncGuncelle(
    IN p_OduncID INT,
    IN p_OgrenciID INT,
    IN p_KitapID INT,
    IN p_GorevliID INT,
    IN p_OduncTarihi DATE,
    IN p_SonTeslimTarihi DATE,
    IN p_IadeTarihi DATE,
    IN p_Durum VARCHAR(50)
)
BEGIN
    UPDATE OduncIslemleri
    SET OgrenciID = p_OgrenciID,
        KitapID = p_KitapID,
        GorevliID = p_GorevliID,
        OduncTarihi = p_OduncTarihi,
        SonTeslimTarihi = p_SonTeslimTarihi,
        IadeTarihi = p_IadeTarihi,
        Durum = p_Durum
    WHERE OduncID = p_OduncID;
END $$

-- D3. Ödünç Silme
CREATE PROCEDURE sp_OduncSil(
    IN p_OduncID INT
)
BEGIN
    DELETE FROM OduncIslemleri WHERE OduncID = p_OduncID;
END $$

-- D4. Ödünç Listeleme
CREATE PROCEDURE sp_OduncListele()
BEGIN
    SELECT OduncID, OgrenciID, KitapID, GorevliID, OduncTarihi, SonTeslimTarihi, IadeTarihi, Durum FROM OduncIslemleri;
END $$

-- ----------------------------------------------------------------------------
-- E. Cezalar Tablosu CRUD Yordamları
-- ----------------------------------------------------------------------------

-- E1. Ceza Ekleme
CREATE PROCEDURE sp_CezaEkle(
    IN p_OgrenciID INT,
    IN p_OduncID INT,
    IN p_CezaTutari DECIMAL(10, 2),
    IN p_Aciklama TEXT,
    IN p_CezaTarihi DATE,
    IN p_OdendiMi BOOLEAN
)
BEGIN
    INSERT INTO Cezalar (OgrenciID, OduncID, CezaTutari, Aciklama, CezaTarihi, OdendiMi)
    VALUES (p_OgrenciID, p_OduncID, p_CezaTutari, p_Aciklama, COALESCE(p_CezaTarihi, CURDATE()), p_OdendiMi);
END $$

-- E2. Ceza Güncelleme
CREATE PROCEDURE sp_CezaGuncelle(
    IN p_CezaID INT,
    IN p_OgrenciID INT,
    IN p_OduncID INT,
    IN p_CezaTutari DECIMAL(10, 2),
    IN p_Aciklama TEXT,
    IN p_CezaTarihi DATE,
    IN p_OdendiMi BOOLEAN
)
BEGIN
    UPDATE Cezalar
    SET OgrenciID = p_OgrenciID,
        OduncID = p_OduncID,
        CezaTutari = p_CezaTutari,
        Aciklama = p_Aciklama,
        CezaTarihi = p_CezaTarihi,
        OdendiMi = p_OdendiMi
    WHERE CezaID = p_CezaID;
END $$

-- E3. Ceza Silme
CREATE PROCEDURE sp_CezaSil(
    IN p_CezaID INT
)
BEGIN
    DELETE FROM Cezalar WHERE CezaID = p_CezaID;
END $$

-- E4. Ceza Listeleme
CREATE PROCEDURE sp_CezaListele()
BEGIN
    SELECT CezaID, OgrenciID, OduncID, CezaTutari, Aciklama, CezaTarihi, OdendiMi FROM Cezalar;
END $$

DELIMITER ;


-- ============================================================================
-- 5. ÖRNEK VERİ EKLEME (SAMPLE DATA)
-- ============================================================================

-- A. Öğrenciler (10 Adet)
INSERT INTO Ogrenciler (AdSoyad, OgrenciNo, Bolum, Telefon, Eposta, KayitTarihi) VALUES
('Ahmet Yılmaz', '2021001', 'Bilgisayar Mühendisliği', '05551234567', 'ahmet.yilmaz@univ.edu.tr', '2025-09-15'),
('Ayşe Kaya', '2021002', 'Yazılım Mühendisliği', '05552345678', 'ayse.kaya@univ.edu.tr', '2025-09-15'),
('Mehmet Demir', '2021003', 'Elektrik-Elektronik Mühendisliği', '05553456789', 'mehmet.demir@univ.edu.tr', '2025-09-16'),
('Fatma Şahin', '2021004', 'Endüstri Mühendisliği', '05554567890', 'fatma.sahin@univ.edu.tr', '2025-09-16'),
('Mustafa Çelik', '2021005', 'Makine Mühendisliği', '05555678901', 'mustafa.celik@univ.edu.tr', '2025-09-17'),
('Emine Öztürk', '2021006', 'Tıp Fakültesi', '05556789012', 'emine.ozturk@univ.edu.tr', '2025-09-17'),
('Ali Can', '2021007', 'Hukuk Fakültesi', '05557890123', 'ali.can@univ.edu.tr', '2025-09-18'),
('Hatice Aslan', '2021008', 'İktisat', '05558901234', 'hatice.aslan@univ.edu.tr', '2025-09-18'),
('Hüseyin Koç', '2021009', 'Mimarlık', '05559012345', 'huseyin.koc@univ.edu.tr', '2025-09-19'),
('Zeynep Bulut', '2021010', 'Psikoloji', '05550123456', 'zeynep.bulut@univ.edu.tr', '2025-09-19');

-- B. Kitaplar (20 Adet)
INSERT INTO Kitaplar (KitapAdi, Yazar, Yayinevi, YayinYili, ISBN, ToplamKopya, MevcutKopya) VALUES
('Nutuk', 'Mustafa Kemal Atatürk', 'Ata Yayıncılık', 1927, '9789753450010', 5, 5),
('Çalıkuşu', 'Reşat Nuri Güntekin', 'İnkılap Kitabevi', 1922, '9789751000027', 3, 3),
('Kürk Mantolu Madonna', 'Sabahattin Ali', 'Yapı Kredi Yayınları', 1943, '9789750807038', 4, 4),
('İnce Memed', 'Yaşar Kemal', 'Yapı Kredi Yayınları', 1955, '9789750800046', 3, 3),
('Saatleri Ayarlama Enstitüsü', 'Ahmet Hamdi Tanpınar', 'Dergah Yayınları', 1961, '9789757321056', 2, 2),
('Tutunamayanlar', 'Oğuz Atay', 'İletişim Yayınları', 1972, '9789754700063', 3, 3),
('Yaban', 'Yakup Kadri Karaosmanoğlu', 'İletişim Yayınları', 1932, '9789754700070', 2, 2),
('Eylül', 'Mehmet Rauf', 'Can Yayınları', 1901, '9789750700085', 2, 2),
('Felatun Bey ile Rakım Efendi', 'Ahmet Mithat Efendi', 'Everest Yayınları', 1875, '9786051410091', 3, 3),
('Aşk-ı Memnu', 'Halit Ziya Uşaklıgil', 'Can Yayınları', 1900, '9789750700108', 4, 4),
('Mai ve Siyah', 'Halit Ziya Uşaklıgil', 'Can Yayınları', 1897, '9789750700115', 3, 3),
('Yaprak Dökümü', 'Reşat Nuri Güntekin', 'İnkılap Kitabevi', 1930, '9789751000126', 3, 3),
('Huzur', 'Ahmet Hamdi Tanpınar', 'Dergah Yayınları', 1949, '9789757321131', 2, 2),
('Dokuzuncu Hariciye Koğuşu', 'Peyami Safa', 'Ötüken Neşriyat', 1930, '9789754370140', 3, 3),
('Fatih-Harbiye', 'Peyami Safa', 'Ötüken Neşriyat', 1931, '9789754370157', 3, 3),
('Sinekli Bakkal', 'Halide Edib Adıvar', 'Can Yayınları', 1935, '9789750700164', 3, 3),
('Sergüzeşt', 'Samipaşazade Sezai', 'İş Bankası Kültür Yayınları', 1888, '9789944880176', 2, 2),
('Araba Sevdası', 'Recaizade Mahmut Ekrem', 'İş Bankası Kültür Yayınları', 1898, '9789944880183', 2, 2),
('Taaşşuk-ı Talat ve Fitnat', 'Şemsettin Sami', 'İş Bankası Kültür Yayınları', 1872, '9789944880190', 2, 2),
('Vatan Yahut Silistre', 'Namık Kemal', 'İş Bankası Kültür Yayınları', 1873, '9789944880206', 2, 2);

-- C. Kütüphane Görevlileri (3 Adet)
INSERT INTO KutuphaneGorevlileri (AdSoyad, Telefon, Eposta, KullaniciAdi, Sifre) VALUES
('Süleyman Yılmaz', '05441112233', 'suleyman.yilmaz@univ.edu.tr', 'suleyman_g', 'sifre123'),
('Merve Aslan', '05442223344', 'merve.aslan@univ.edu.tr', 'merve_g', 'mervePass'),
('Kemal Koç', '05443334455', 'kemal.koc@univ.edu.tr', 'kemal_g', 'kemalSecure');

-- D. Ödünç Alma İşlemleri (10 Adet)
-- Not: TRG_KitapOduncVer tetikleyicisi bu satırların eklenmesiyle Kitaplar tablosundaki MevcutKopya sayılarını otomatik 1 azaltacaktır.
INSERT INTO OduncIslemleri (OgrenciID, KitapID, GorevliID, OduncTarihi, SonTeslimTarihi, IadeTarihi, Durum) VALUES
(1, 1, 1, '2026-05-01', '2026-05-15', NULL, 'Ödünç Verildi'),
(2, 2, 1, '2026-05-02', '2026-05-16', NULL, 'Ödünç Verildi'),
(3, 3, 2, '2026-05-03', '2026-05-17', NULL, 'Ödünç Verildi'),
(4, 4, 2, '2026-05-04', '2026-05-18', NULL, 'Ödünç Verildi'),
(5, 5, 3, '2026-05-05', '2026-05-19', NULL, 'Ödünç Verildi'),
(6, 6, 3, '2026-05-06', '2026-05-20', NULL, 'Ödünç Verildi'),
(7, 7, 1, '2026-05-07', '2026-05-21', NULL, 'Ödünç Verildi'),
(8, 8, 2, '2026-05-08', '2026-05-22', NULL, 'Ödünç Verildi'),
(9, 9, 3, '2026-05-09', '2026-05-23', NULL, 'Ödünç Verildi'),
(10, 10, 1, '2026-05-10', '2026-05-24', NULL, 'Ödünç Verildi');

-- E. Geri İade ve Ceza Tetikleme Güncellemeleri
-- Geri iadeleri güncelleyerek TRG_KitapIadeEt tetikleyicisini çalıştırıyoruz.
-- Bu tetikleyici, gecikmiş olan iadelerde otomatik olarak 'Cezalar' tablosuna 5 adet ceza kaydı ekleyecektir.

-- Gecikmiş İadeler (Otomatik Olarak 5 Ceza Kaydı Oluşturacaktır)
-- 1. OduncID = 1: Son teslim 15 Mayıs, İade 20 Mayıs (5 Gün Gecikme -> 5 * 5 = 25.00 TL)
UPDATE OduncIslemleri SET IadeTarihi = '2026-05-20', Durum = 'İade Edildi' WHERE OduncID = 1;

-- 2. OduncID = 2: Son teslim 16 Mayıs, İade 26 Mayıs (10 Gün Gecikme -> 10 * 5 = 50.00 TL)
UPDATE OduncIslemleri SET IadeTarihi = '2026-05-26', Durum = 'İade Edildi' WHERE OduncID = 2;

-- 3. OduncID = 3: Son teslim 17 Mayıs, İade 22 Mayıs (5 Gün Gecikme -> 5 * 5 = 25.00 TL)
UPDATE OduncIslemleri SET IadeTarihi = '2026-05-22', Durum = 'İade Edildi' WHERE OduncID = 3;

-- 4. OduncID = 4: Son teslim 18 Mayıs, İade 21 Mayıs (3 Gün Gecikme -> 3 * 5 = 15.00 TL)
UPDATE OduncIslemleri SET IadeTarihi = '2026-05-21', Durum = 'İade Edildi' WHERE OduncID = 4;

-- 5. OduncID = 5: Son teslim 19 Mayıs, İade 27 Mayıs (8 Gün Gecikme -> 8 * 5 = 40.00 TL)
UPDATE OduncIslemleri SET IadeTarihi = '2026-05-27', Durum = 'İade Edildi' WHERE OduncID = 5;

-- Zamanında Yapılan İadeler (Ceza Oluşmayacaktır)
-- 6. OduncID = 6: Son teslim 20 Mayıs, İade 18 Mayıs (Erken teslim)
UPDATE OduncIslemleri SET IadeTarihi = '2026-05-18', Durum = 'İade Edildi' WHERE OduncID = 6;

-- 7. OduncID = 7: Son teslim 21 Mayıs, İade 21 Mayıs (Tam zamanında teslim)
UPDATE OduncIslemleri SET IadeTarihi = '2026-05-21', Durum = 'İade Edildi' WHERE OduncID = 7;

-- Kalan 3 ödünç işlemi (OduncID = 8, 9, 10) aktif ödünç olarak kalmaya devam edecektir.
