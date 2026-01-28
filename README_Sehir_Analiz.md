# Şehir ve İlçe Verisi Karşılaştırma Aracı Dokümantasyonu

Bu doküman, güncel şehir/ilçe listesi (`güncelliste-1.groovy`) ile veritabanı dosyaları (`admin-sehir.sql` ve `v1-sehir.sql`) arasındaki veri tutarlılığını kontrol etmek için hazırlanan Python betiği (`compare_districts_v2.py`) hakkında bilgi içerir.

## 1. Amacı
Projenizdeki mevcut veritabanı yedeklerinde (`.sql` dosyaları) bulunan şehir ve ilçe kayıtlarının, referans alınan güncel listeye (`.groovy` dosyası) göre eksiklerini tespit etmektir. Özellikle yeni ilçe olan yerlerin veya ismi değişen bölgelerin tespiti için kullanılır.

## 2. Gereksinimler
*   **Python 3.x:** Scripti çalıştırmak için bilgisayarınızda Python yüklü olmalıdır. (Terminalde `python3 --version` yazarak kontrol edebilirsiniz).
*   **Ek Kütüphane:** Standart kütüphaneler (`re`, `os`, `sys`) kullanıldığı için ekstra kurulum (`pip install` vb.) gerekmez.

## 3. Dosya Yapısı
Scriptin doğru çalışabilmesi için aşağıdaki dosyaların betik içerisinde belirtilen dizinde veya script ile aynı dizinde olması beklenir:

1.  `compare_districts_v2.py`: Analizi yapan Python betiği.
2.  `güncelliste-1.groovy`: Referans alınan güncel şehir ve ilçelerin bulunduğu dosya.
3.  `admin-sehir.sql`: Kontrol edilecek 1. SQL veritabanı dökümü.
4.  `v1-sehir.sql`: Kontrol edilecek 2. SQL veritabanı dökümü.

*(Script içerisinde dosya yolları `/Users/hnidakd/...` şeklinde tam yol olarak tanımlanmıştır. Dosyaların yerini değiştirirseniz script içindeki `base_dir` veya dosya yolu değişkenlerini güncellemeniz gerekebilir.)*

## 4. Kullanım

Terminal uygulamasını açın ve scriptin bulunduğu dizine gidin (veya scripti tam yoluyla çağırın).

```bash
# Scripti çalıştırma komutu
python3 compare_districts_v2.py
```

## 5. Çıktı ve Raporlama
Script çalıştığında iki türlü çıktı üretir:

1.  **Terminal Ekranı:** Analiz ilerleyişini, yüklenen il sayılarını ve özet eksiklikleri ekrana basar.
2.  **Rapor Dosyası (`eksik_ilceler_raporu.txt`):** Analiz tamamlandığında scriptin çalıştığı dizinde oluşturulur.

### Rapor İçeriği Örneği
Rapor dosyasında her il için **eksik** olan (güncel listede olup SQL'de olmayan) ve **fazla/eski** olan (SQL'de olup güncel listede olmayan) ilçeler listelenir:

```text
====================
Analyzing admin-sehir...
====================
[ANKARA] Eksik İlçeler (Eklemeniz Gerekenler): Kahramankazan
    -> [ANKARA] Fazla/Eski Kayıtlar (Silmeniz/Düzenlemeniz Gerekenler): Kazan, Merkez

[ISTANBUL] Eksik İlçeler (Eklemeniz Gerekenler): Eyüpsultan
    -> [ISTANBUL] Fazla/Eski Kayıtlar (Silmeniz/Düzenlemeniz Gerekenler): Eyüp

[MANISA] Eksik İlçeler (Eklemeniz Gerekenler): Yunusemre, Şehzadeler
    -> [MANISA] Fazla/Eski Kayıtlar (Silmeniz/Düzenlemeniz Gerekenler): Merkez
...
Total missing in admin-sehir: 25
```

*   **Eksik İlçeler**: Veritabanına eklenmesi gereken yeni ilçelerdir.
*   **Fazla/Eski Kayıtlar**: Veritabanından silinmesi veya isminin güncellenmesi gereken kayıtlardır (Sıklıkla "Merkez" kayıtları veya eski ilçe isimleri burada çıkar).

## 6. Sık Karşılaşılan Durumlar
*   **"CRITICAL: Province ... not found" Hatası:** SQL dosyasında ilgili ilin kaydı hiç bulunamazsa bu hata alınır. Genellikle "Amasya" gibi karakter sorunu olabilen veya "İstanbul" gibi veritabanında "Avrupa/Anadolu" diye ayrılmış illerde görülebilir. Script bu durumlar için özel eşleştirme kuralları içerir.
*   **Merkez İlçeler:** Bazı veritabanlarında merkez ilçe sadece "Merkez" olarak geçerken, güncel listede "Efeler", "Merkezefendi" gibi özel isimler alabilir. Bu durumlar raporda "Eksik" olarak görünecektir; manuel kontrol edilip veritabanında isim değişikliği yapılmalıdır.

## 7. Scriptin Çalışma Mantığı
1.  **Veri Okuma:** `.groovy` dosyasını satır satır okuyup regex ile `1   İLÇE   İL` formatını ayrıştırır. SQL dosyalarını okuyup `INSERT INTO ...` komutlarını regex ile parçalar.
2.  **Karşılaştırma:** Referans listedeki her ilçe için veritabanında (birebir veya kapsayan) bir eşleşme arar. Bulamazsa listeye ekler.

## 8. Veri Temizleme ve Normalizasyon
Script, hatalı "eksik" uyarısı vermemek için metinleri karşılaştırmadan önce şu işlemleri uygular:

*   **Boşluk Temizliği (Whitespace Trimming):** Veritabanındaki kayıtların başında veya sonunda unutulan boşluklar (Örn: `"Alaşehir "`) otomatik temizlenir.
*   **Türkçe Karakter Eşitleme:** "I" harfi "ı" olurken, "İ" harfi "i"ye dönüştürülür. Standart küçük harfe çevirme fonksiyonlarının yetersiz kaldığı durumlar için özel bir haritalama tablosu kullanılır.
*   **Şapkalı Harf Düzeltmesi:** "Kâğıthane" veya "Hakkâri" gibi kullanımlardaki şapkalı harfler normal harflere (â -> a, î -> i, û -> u) çevrilir, böylece yazım farklarından kaynaklı hatalar önlenir.

## 9. İstanbul ve Karmaşık SQL Yapıları
*   **Parantezli İsimler:** Veritabanında "İstanbul (Avrupa)" ve "İstanbul (Anadolu)" şeklinde parantez içeren kayıtlar, standart okuma yöntemlerini (regex) bozabilir. Script, SQL dosyasını `INSERT INTO` bloklarına bölerek okuduğu için bu tür parantezli değerleri artık hatasız işlemektedir.
*   **İsim Değişiklikleri:** Örneğin "Eyüpsultan" ilçesi güncel listededir ancak eski veritabanlarında "Eyüp" olarak geçiyor olabilir. Script, tam eşleşme aradığı için bu tür durumları "Eksik: Eyüpsultan" olarak raporlar. Bu, veritabanının güncellenmesi gerektiğinin bir işaretidir.



---
*Oluşturulma Tarihi: 28 Ocak 2026*
