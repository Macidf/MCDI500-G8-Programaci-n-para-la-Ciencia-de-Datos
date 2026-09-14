# Guía de trabajo con Git para el equipo

## Ramas

| Rama | Uso |
|---|---|
| `main` | Versión entregable. Sólo recibe merges al cerrar una fase. |
| `dev` | Integración del trabajo en curso. |
| `feature/<tema>` | Trabajo individual (opcional), p. ej. `feature/validacion`. |

## Primera vez (cada integrante)

```bash
git clone https://github.com/Macidf/MCDI500-G8-Programaci-n-para-la-Ciencia-de-Datos.git
cd MCDI500-G8-Programaci-n-para-la-Ciencia-de-Datos

# Identidad: debe coincidir con tu cuenta de GitHub para que tus commits se te atribuyan
git config user.name "Nombre Apellido"
git config user.email "tu-correo-de-github@ejemplo.com"

git checkout dev
```

El dueño del repositorio debe agregar a cada integrante como colaborador en
**Settings → Collaborators** para que pueda hacer `push`.

## Ciclo de trabajo

```bash
git checkout dev
git pull                               # traer lo último antes de empezar

# ... trabajar ...

git status                             # revisar qué cambió
git add F2/F2_03_Validacion.ipynb      # agregar archivos concretos, no "git add ." a ciegas
git commit -m "test: agrega casos límite de interpolación en F2-03"
git push
```

## Mensajes de commit

Formato: `tipo: descripción en presente y en minúscula`

| Tipo | Cuándo |
|---|---|
| `feat` | Nueva funcionalidad (módulo, notebook, etapa del pipeline) |
| `fix` | Corrección de un error |
| `docs` | README, bitácora, markdown de notebooks |
| `test` | Pruebas de validación |
| `refactor` | Reorganizar código sin cambiar su comportamiento |
| `chore` | Entorno, dependencias, `.gitignore` |

Buenos ejemplos:
- `feat: agrega etapa de anulación de fallos de sensor`
- `fix: la interpolación ya no rellena el inicio de huecos largos`
- `docs: justifica la elección de Ponds data.csv`

Evitar: `cambios`, `update`, `final`, `ahora sí`.

## Contribuciones individuales

La rúbrica evalúa **commits identificables por integrante**. Por eso:

- Cada integrante hace sus **propios** commits desde su equipo y con su identidad.
- Commits pequeños y frecuentes: uno por tarea terminada, no uno gigante al final.
- No hacer commits en nombre de otro integrante.

## Cerrar una fase

```bash
git checkout main
git pull
git merge --no-ff dev -m "merge: cierre de Fase 2"
git push
git checkout dev
```

## Notebooks y conflictos

Los `.ipynb` son JSON y generan conflictos difíciles de resolver. Para evitarlos:

- Coordinar quién edita cada notebook; no editar el mismo notebook a la vez.
- Antes de hacer commit de un notebook, **reiniciar el kernel y ejecutar todo**, para que
  las salidas guardadas correspondan al código.

## Qué no se sube

Definido en `.gitignore`: `.venv/`, `data/raw/*` (salvo su README), `data/processed/*.csv`,
documentos `.docx`/`.pdf` y archivos temporales. Los datos se regeneran ejecutando los
notebooks.
