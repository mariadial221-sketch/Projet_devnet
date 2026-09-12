# Rapport Automatique de Déploiement DEVNET

**Projet :** Projet10  
**Date de génération :** 2026-09-12 11:53:43  
**Projet GNS3 lié :** `e540a7c8-4128-45a1-9ffe-31b97e6326ca`

## 1. Contexte & Topologie Déployée
Déploiement automatisé d'une infrastructure bi-site (LAN A / LAN B) reliée par un lien inter-site routé, avec réseau de management, via l'API REST GNS3 et Netmiko.

## 2. Équipements Déployés

| Équipement | Type | IP de management |
|---|---|---|
| SW_L23_1 | Switch L23 | 192.168.100.6 |
| R1 | Switch L23 | 192.168.100.1 |
| R2 | Switch L3 | 192.168.100.2 |
| SW2 | Switch L23 | 192.168.100.7 |
| PC1 | VPCS | 192.168.1.10 |
| PC2 | VPCS | 192.168.2.10 |

## 3. Configuration Appliquée

### SW_L23_1 — ✅ SUCCÈS
```
vlan 10
SW_L23_1(config-vlan)#
SW_L23_1(config-vlan)#
name ADMINISTRATION
SW_L23_1(config-vlan)#
SW_L23_1(config-vlan)#
vlan 20
SW_L23_1(config-vlan)#
SW_L23_1(config-vlan)#
name PEDAGOGIE
SW_L23_1(config-vlan)#
SW_L23_1(config-vlan)#
interface Ethernet0/0
SW_L23_1(config-if)#
SW_L23_1(config-if)#
switchport mode access
SW_L23_1(config-if)#
SW_L23_1(config-if)#
switchport access vlan 10
SW_L23_1(config-if)#
SW_L23_1(config-if)#
interface Ethernet0/1
SW_L23_1(config-if)#
SW_L23_1(config-if)#
no switchport
SW_L23_1(config-if)#
SW_L23_1(config-if)#
ip address 192.168.1.2 255.255.255.0
SW_L23_1(config-if)#
SW_L23_1(config-if)#
no shutdown
SW_L23_1(config-if)#
SW_L23_1(config-if)#
ip routing
SW_L23_1(config)#
SW_L23_1(config)#
ip route 0.0.0.0 0.0.0.0 192.168.1.1
SW_L23_1(config)#
SW_L23_1(config)#
end
SW_L23_1#
SW_L23_1#
write memory
Building configuration...
Compressed configuration from 1519 bytes to 923 bytes[OK]
SW_L23_1#
SW_L23_1#
```

### R1 — ✅ SUCCÈS
```
interface Ethernet0/0
R1(config-if)#
R1(config-if)#
no switchport
R1(config-if)#
R1(config-if)#
ip address 192.168.1.1 255.255.255.0
R1(config-if)#
R1(config-if)#
no shutdown
R1(config-if)#
R1(config-if)#
interface Ethernet0/1
R1(config-if)#
R1(config-if)#
no switchport
R1(config-if)#
R1(config-if)#
ip address 10.0.0.1 255.255.255.252
R1(config-if)#
R1(config-if)#
no shutdown
R1(config-if)#
R1(config-if)#
interface Ethernet1/0
R1(config-if)#
R1(config-if)#
no switchport
R1(config-if)#
R1(config-if)#
ip address 192.168.100.1 255.255.255.0
R1(config-if)#
R1(config-if)#
no shutdown
R1(config-if)#
R1(config-if)#
ip routing
R1(config)#
R1(config)#
ip route 192.168.2.0 255.255.255.0 10.0.0.2
R1(config)#
R1(config)#
end
R1#
R1#
write memory
Building configuration...
Compressed configuration from 1602 bytes to 955 bytes[OK]
R1#
R1#
```

### R2 — ✅ SUCCÈS
```
interface Ethernet0/0
R2(config-if)#
R2(config-if)#
no switchport
R2(config-if)#
R2(config-if)#
ip address 192.168.2.1 255.255.255.0
R2(config-if)#
R2(config-if)#
no shutdown
R2(config-if)#
R2(config-if)#
interface Ethernet0/1
R2(config-if)#
R2(config-if)#
no switchport
R2(config-if)#
R2(config-if)#
ip address 10.0.0.2 255.255.255.252
R2(config-if)#
R2(config-if)#
no shutdown
R2(config-if)#
R2(config-if)#
interface Ethernet1/0
R2(config-if)#
R2(config-if)#
no switchport
R2(config-if)#
R2(config-if)#
ip address 192.168.100.2 255.255.255.0
R2(config-if)#
R2(config-if)#
no shutdown
R2(config-if)#
R2(config-if)#
ip routing
R2(config)#
R2(config)#
ip route 192.168.1.0 255.255.255.0 10.0.0.1
R2(config)#
R2(config)#
end
R2#
R2#
write memory
Building configuration...
Compressed configuration from 1602 bytes to 962 bytes[OK]
R2#
R2#
```

### SW2 — ✅ SUCCÈS
```
interface Ethernet0/1
SW2(config-if)#
SW2(config-if)#
no switchport
SW2(config-if)#
SW2(config-if)#
ip address 192.168.2.2 255.255.255.0
SW2(config-if)#
SW2(config-if)#
no shutdown
SW2(config-if)#
SW2(config-if)#
ip routing
SW2(config)#
SW2(config)#
ip route 0.0.0.0 0.0.0.0 192.168.2.1
SW2(config)#
SW2(config)#
end
SW2#
SW2#
write memory
Building configuration...
Compressed configuration from 1463 bytes to 889 bytes[OK]
SW2#
SW2#
```

### PC1 — ✅ SUCCÈS
```
VPCS ignoré (pas de configuration IOS applicable).
```

### PC2 — ✅ SUCCÈS
```
VPCS ignoré (pas de configuration IOS applicable).
```

## 4. Extension Obligatoire — VLANs

Extension choisie : **configuration de VLANs** sur `SW_L23_1` (VLAN 10 - ADMINISTRATION, VLAN 20 - PEDAGOGIE), avec routage statique assurant la connectivité inter-LAN.

## 5. Tests de Validation

- Ping **SW_L23_1** → `192.168.1.1` : ✅ SUCCÈS
- Ping **R1** → `192.168.1.2` : ✅ SUCCÈS
- Ping **R1** → `10.0.0.2` : ✅ SUCCÈS
- Ping **R2** → `192.168.2.2` : ✅ SUCCÈS
- Ping **R2** → `10.0.0.1` : ✅ SUCCÈS
- Ping **SW2** → `192.168.2.1` : ✅ SUCCÈS
- SW_L23_1 (test inter-LAN) → `192.168.2.2` : ✅ SUCCÈS
- SW2 (test inter-LAN) → `192.168.1.2` : ✅ SUCCÈS

## Bilan Final : **✅ SUCCÈS**
