# SDKM-PoC: Arquitetura para Integração Contínua de Chaves Híbridas Quanticamente Seguras

Este repositório contém a implementação de referência e os artefatos experimentais apresentados no artigo submetido ao **SBRC 2026**. A Prova de Conceito (PoC) demonstra uma arquitetura de **Software-Defined Key Management (SDKM)** projetada para mitigar a ameaça **Harvest Now, Decrypt Later (HN-DL)** por meio da orquestração contínua de chaves híbridas em redes clássicas.

 

## 📑 Resumo do Projeto

A solução propõe o desacoplamento da lógica de segurança do plano de dados por meio de um controlador centralizado. A arquitetura viabiliza a **Forward Secrecy Quântica** através do mecanismo de **Hot Key Rotation** (rotação de chaves em tempo de execução), permitindo a substituição do material criptográfico em túneis IPsec ativos sem a necessidade de renegociação de sessão (*handshake*) ou interrupção do tráfego.



## 🏗️ Arquitetura do Sistema

O sistema é estruturado em três domínios principais:

- **SDKM Core (Orquestrador)**:  
  Plano de controle lógico responsável pela geração de entropia PQC, consumo de chaves QKD e orquestração do ciclo de vida das chaves.

- **Quantum Plane Forwarding**:  
  Provê entropia física via nós QKD (emulados pela ferramenta *QuKayDee*), seguindo o padrão **ETSI GS QKD 014**.

- **Hosts (Agentes de Segurança)**:  
  Executam a injeção transparente de chaves nos serviços de rede (*strongSwan*) utilizando a interface **VICI**.



## 🛠️ Especificações Técnicas

- **Criptografia Pós-Quântica (PQC)**:  
  Utilização da biblioteca **libOQS** com os algoritmos **ML-KEM-768** (confidencialidade) e **ML-DSA-65** (autenticidade) no plano de controle.

- **Hibridização de Chaves**:  
  Processo de mixagem baseado em **XOR**, seguido de derivação via **HKDF-SHA256**, garantindo segurança por composição (PQC + QKD).

- **VPN IPsec**:  
  Utilização do daemon **strongSwan** no kernel Linux para o plano de dados.

- **Ambiente**:  
  Virtualização baseada em **Docker**, com controle de condições de rede (latência WAN de 20 ms a 150 ms) via **tc/netem**.



## 📊 Cenários Experimentais

O repositório está organizado para reproduzir os resultados das Seções 5 e 6 do artigo:

- **Cenário Baseline**:  
  Operação de uma VPN IPsec clássica para estabelecer métricas de comparação.

- **Cenário SDKM (Híbrido)**:  
  Avaliação da latência de hibridização e injeção, além do impacto em vazão TCP e *jitter* UDP sob rotação proativa.

- **Escalabilidade Multi-nó**:  
  Testes com múltiplos túneis simultâneos (Alice–Bob e Carol–Dave) para validar o paralelismo do Orquestrador.


## 📂 Estrutura do Repositório

- `/scripts`  
  Código-fonte do orquestrador, agentes e lógica de hibridização.

- `automation_controller.py`  
  Orquestrador dos testes automatizados.



## 🚀 Como Executar
Os testes realizados nesse experimento consiste em ciclo de testes que contem os seguintes:

- ### Cenario Baseline:
    Para rodar o teste baseline devemos rodar o script `baseline_automation.py` na pasta `\baseline_test`:

    ```python
        python3 baseline_automation.py --iteration 60 --duration 300 --interval 60
    ``` 
- ### Cenario SDKM:
    Para rodar o teste SDKM devemos rodar o script `automation_controller.py` na pasta `\scripts`:

    ```python
        python3 automation_controller.py --iteration 60 --duration 300 --interval 60
    ``` 

**Nota**: Para reproduzir os resultados de latência de orquestração detalhados na Figura 2 do artigo, certifique-se de que o emulador **QuKayDee** está acessível via API REST. O tutorial de como usar o simulador está no site dele. [Tutorial](https://qukaydee.com/pages/getting_started)



## 🎓 Citação

Se você utilizar este código em sua pesquisa, por favor cite o artigo correspondente:

```bibtex
@inproceedings{silva2026arquitetura,
  title={Arquitetura para Integração Contínua de Chaves Híbridas Quanticamente Seguras},
  author={Silva, Esdras V. and Abreu, Diego and Abelém, Antônio},
  booktitle={Anais do XLIV Simpósio Brasileiro de Redes de Computadores e Sistemas Distribuídos (SBRC 2026)},
  year={2026},
  organization={SBC}
}
```

## 🤝 Agradecimentos

Este trabalho foi realizado com o apoio da UFPA (Propesp), CNPq e FAPESP.
