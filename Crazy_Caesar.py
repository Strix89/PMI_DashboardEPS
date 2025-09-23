MESSAGGIO = ""

def cifra_cesare_parole(messaggio):
    parole = messaggio.split()
    parole_cifrate = []
    chiave = 1
    
    for parola in parole:
        parola_cifrata = ""
        for carattere in parola:
            if carattere.isalpha():
                # Determina se il carattere è maiuscolo o minuscolo
                base = ord('A') if carattere.isupper() else ord('a')
                # Applica il cifrario di Cesare con la chiave corrente
                nuovo_carattere = chr((ord(carattere) - base + chiave) % 26 + base)
                parola_cifrata += nuovo_carattere
            else:
                # Mantieni i caratteri non alfabetici invariati
                parola_cifrata += carattere
        parole_cifrate.append(parola_cifrata)
        chiave += 1  # Incrementa la chiave per la prossima parola
    
    return ' '.join(parole_cifrate)

# Esecuzione del programma
if __name__ == "__main__":
    risultato = cifra_cesare_parole(MESSAGGIO)
    print("Messaggio originale:", MESSAGGIO)
    print("Messaggio cifrato:", risultato)