from fastapi import FastAPI, Depends
from fastapi.security import OAuth2PasswordBearer
from app.databases import engine, Base
from app import netmiko_routes
from app.routes.gns3 import router as gns3_router
from app.routes import equipements, topologie, auth, interfaces

# Création des tables
Base.metadata.create_all(bind=engine)

# Déclaration de la sécurité OAuth2 pour Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

app = FastAPI(
    title="DEVNET Automation API",
    description="API FastAPI pour la gestion d'inventaire, le déploiement GNS3 et l'automatisation Netmiko",
    version="1.0.0"
)

# Inclusion de tous les routeurs
app.include_router(equipements.router)
app.include_router(interfaces.router)  # Ajout de la section Interfaces
app.include_router(topologie.router)
app.include_router(auth.router_users)
app.include_router(auth.router)
app.include_router(netmiko_routes.router)
app.include_router(gns3_router)

# Route de test sécurisée pour forcer l'affichage du bouton Authorize
@app.get("/me", tags=["Authentification"])
def read_current_user(token: str = Depends(oauth2_scheme)):
    return {"token": token}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)