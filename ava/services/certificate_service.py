from django.utils import timezone
from ava.models import MatriculaCurso, Certificado, ConfigCertificado

class CertificacaoService:
    @staticmethod
    def avaliar_e_emitir(matricula: MatriculaCurso):
        """
        Avalia se a matrícula cumpre todos os requisitos e emite o certificado se configurado.
        """
        curso = matricula.curso
        
        # 1. Curso permite certificado?
        if not curso.permite_certificado:
            return False, "Curso não emite certificado"

        # 2. Tem configuração de certificado ativa?
        try:
            config = ConfigCertificado.objects.get(curso=curso)
        except ConfigCertificado.DoesNotExist:
            return False, "Configuração de certificado não encontrada para este curso"
        
        # 3. Atingiu progresso mínimo?
        if matricula.progresso_percentual < curso.progresso_minimo:
            return False, f"Progresso insuficiente: {matricula.progresso_percentual}% de {curso.progresso_minimo}%"
            
        # 4. Atingiu nota mínima?
        if matricula.nota_final_obtida < curso.nota_minima:
            return False, f"Nota insuficiente: {matricula.nota_final_obtida} de {curso.nota_minima}"

        # 5. Já possui certificado?
        if hasattr(matricula, 'certificado_emitido') and matricula.certificado_emitido is not None:
            return True, "Certificado já emitido anteriormente"

        # 6. Emitir certificado
        carga_horaria = config.carga_horaria_impressa if config.carga_horaria_impressa > 0 else curso.carga_horaria
        
        dados_impressos = {
            "aluno_nome": matricula.aluno.get_full_name() or matricula.aluno.username,
            "curso_nome": curso.titulo,
            "carga_horaria": carga_horaria,
            "data_emissao": timezone.now().isoformat(),
            "nota_final": float(matricula.nota_final_obtida)
        }

        certificado = Certificado.objects.create(
            matricula_curso=matricula,
            aluno=matricula.aluno,
            nota_final=matricula.nota_final_obtida,
            carga_horaria=carga_horaria,
            dados_impressos=dados_impressos
        )
        
        return True, certificado
