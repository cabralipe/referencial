import { FormEvent, useState, useEffect } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useApiClient } from '@/api/client';

interface CadastroCustom {
  titulo?: string;
  subtitulo?: string;
  label_nome?: string;
  placeholder_nome?: string;
  label_email?: string;
  placeholder_email?: string;
  label_senha?: string;
  label_confirmar_senha?: string;
  label_municipio?: string;
  placeholder_municipio?: string;
  label_escola?: string;
  placeholder_escola?: string;
  label_tipo_usuario?: string;
}

interface ClienteData {
  id: number;
  nome: string;
  cadastro_custom?: CadastroCustom;
}

interface EscolaData {
  id: number;
  nome: string;
  cliente_id: number;
}

interface TipoCadastroData {
  id: number;
  nome: string;
  cliente_id: number;
}

interface CadastroData {
  clientes: ClienteData[];
  escolas: EscolaData[];
  tipos_cadastro: TipoCadastroData[];
}

export function CadastroPage() {
  const { isAuthenticated, status } = useAuth();
  const navigate = useNavigate();
  
  const [nome, setNome] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [selectedTipoCadastroId, setSelectedTipoCadastroId] = useState<number | ''>('');
  
  const api = useApiClient();
  const [clientes, setClientes] = useState<ClienteData[]>([]);
  const [escolas, setEscolas] = useState<EscolaData[]>([]);
  const [tiposCadastro, setTiposCadastro] = useState<TipoCadastroData[]>([]);
  const [selectedClienteId, setSelectedClienteId] = useState<number | ''>('');
  const [selectedEscolaId, setSelectedEscolaId] = useState<number | ''>('');
  const [escolaBusca, setEscolaBusca] = useState('');
  const [isEscolaDropdownOpen, setIsEscolaDropdownOpen] = useState(false);
  const [clienteBusca, setClienteBusca] = useState('');
  const [isClienteDropdownOpen, setIsClienteDropdownOpen] = useState(false);
  
  useEffect(() => {
    async function fetchData() {
      try {
        const response = await api.get<CadastroData>('public/cadastro-data', { skipAuth: true });
        setClientes(response.data.clientes || []);
        setTiposCadastro(response.data.tipos_cadastro || []);

        // Normaliza formatos alternativos de relacionamento cliente/escola.
        const normalizedEscolas: EscolaData[] = (response.data.escolas || [])
          .map((escola: any) => {
            const rawClienteId =
              escola?.cliente_id ??
              escola?.clienteId ??
              (typeof escola?.cliente === 'number' ? escola.cliente : escola?.cliente?.id);
            const clienteId = Number(rawClienteId);
            const escolaId = Number(escola?.id);
            return {
              id: escolaId,
              nome: String(escola?.nome ?? ''),
              cliente_id: Number.isFinite(clienteId) ? clienteId : 0,
            };
          })
          .filter((escola) => Number.isFinite(escola.id) && escola.id > 0 && escola.cliente_id > 0);

        setEscolas(normalizedEscolas);
      } catch (error) {
        console.error('Failed to fetch public data for registration:', error);
      }
    }
    fetchData();
  }, [api]);

  // Escolas filtradas baseadas no cliente selecionado
  // A API não retorna a relação cliente->escola no banco de dados atual para as escolas?
  // Precisamos verificar. Se Escola modelo não tem cliente_id visível no serializer, 
  // pode ser que não funcione o filtro localmente.
  // Wait, let's keep all schools for now if we don't have cliente_id in EscolaData or let's assume filtering.
  
  const [custom, setCustom] = useState<CadastroCustom>({});
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const filteredClientes = clientes.filter((cliente) =>
    cliente.nome.toLowerCase().includes(clienteBusca.toLowerCase())
  );
  const tiposCadastroDoCliente = selectedClienteId
    ? tiposCadastro.filter((tipo) => Number(tipo.cliente_id) === Number(selectedClienteId))
    : [];
  const escolasDoCliente = selectedClienteId
    ? escolas.filter((e) => Number(e.cliente_id) === Number(selectedClienteId))
    : [];
  const filteredEscolas = escolasDoCliente.filter((escola) =>
    escola.nome.toLowerCase().includes(escolaBusca.toLowerCase())
  );

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLocalError(null);

    if (!selectedTipoCadastroId) {
      setLocalError('Por favor, selecione um tipo de usuário.');
      return;
    }

    if (password !== confirmPassword) {
      setLocalError('As senhas não coincidem.');
      return;
    }

    if (!selectedClienteId || !selectedEscolaId) {
      setLocalError('Por favor, selecione um município e escola.');
      return;
    }

    setIsSubmitting(true);
    
    try {
      await api.post('public/cadastro', {
        body: {
          nome,
          email,
          password,
          tipo_cadastro_id: selectedTipoCadastroId,
          cliente_id: selectedClienteId,
          escola_id: selectedEscolaId,
        },
        skipAuth: true
      });
      navigate('/login', { replace: true });
    } catch (err: any) {
      if (err.payload && typeof err.payload === 'object') {
        const p = err.payload as Record<string, any>;
        if (p.email?.length > 0) {
          setLocalError(p.email[0]);
          return;
        }
        if (p.non_field_errors?.length > 0) {
          setLocalError(p.non_field_errors[0]);
          return;
        }
        if (p.cliente_id?.length > 0) {
          setLocalError('Município (Cliente) inválido: ' + p.cliente_id[0]);
          return;
        }
        if (p.escola_id?.length > 0) {
          setLocalError('Escola inválida: ' + p.escola_id[0]);
          return;
        }
      }
      setLocalError(err.message || 'Não foi possível realizar o cadastro. Tente novamente.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-50 font-display text-slate-900 antialiased overflow-x-hidden selection:bg-primary selection:text-white min-h-screen">
      <div className="relative flex flex-col lg:flex-row min-h-screen w-full">
        {/* Desktop Left Side */}
        <div
          className="hidden lg:flex relative w-1/2 bg-gradient-to-br from-blue-600 via-primary to-cyan-400 overflow-hidden items-center justify-center p-12"
          data-alt="Abstract vibrant mesh gradient background in blue and cyan shades"
        >
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 mix-blend-overlay"></div>
          <div className="absolute top-20 right-20 w-96 h-96 bg-cyan-300 rounded-full blur-[100px] opacity-30 mix-blend-screen animate-pulse"></div>
          <div className="absolute bottom-20 left-20 w-96 h-96 bg-blue-500 rounded-full blur-[100px] opacity-40 mix-blend-screen"></div>

          <div className="relative z-10 flex flex-col items-start max-w-lg">
            <div className="mb-8 transform transition-transform hover:scale-105 duration-300 inline-block h-40 overflow-visible flex items-center justify-center">
              <img src={`${import.meta.env.BASE_URL}LOGO_PROLUC.png`} alt="PROLUC Logo" className="h-full w-auto object-contain drop-shadow-xl" />
            </div>
            <p className="text-blue-50 text-xl font-medium opacity-90 leading-relaxed mb-8">
              Junte-se à plataforma de gestão curricular mais inovadora para transformar a educação.
            </p>
            <div className="bg-white/10 backdrop-blur-sm border border-white/20 rounded-3xl p-6 mt-4 w-full">
              <div className="flex items-center gap-4 mb-4">
                <div className="h-3 w-3 rounded-full bg-cyan-300"></div>
                <div className="h-3 w-3 rounded-full bg-blue-300"></div>
                <div className="h-2 w-32 bg-white/20 rounded-full"></div>
              </div>
              <div className="h-32 bg-gradient-to-r from-white/10 to-transparent rounded-xl w-full flex items-center justify-center">
                <span className="material-symbols-outlined text-white/40 text-6xl">school</span>
              </div>
            </div>
          </div>
        </div>

        {/* Mobile Top Header */}
        <div
          className="lg:hidden relative w-full h-[35vh] bg-gradient-to-br from-blue-600 via-primary to-cyan-400 rounded-b-[3rem] overflow-hidden shrink-0 shadow-lg border-b border-white/10"
          data-alt="Abstract vibrant mesh gradient background in blue and cyan shades"
        >
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10 mix-blend-overlay"></div>
          <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-300 rounded-full blur-[80px] opacity-30 mix-blend-screen"></div>
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500 rounded-full blur-[80px] opacity-40 mix-blend-screen"></div>
          <div className="relative z-10 flex flex-col items-center justify-center h-full px-6 pb-8 text-center">
            <div className="mb-4 transform transition-transform hover:scale-105 duration-300 h-16 overflow-visible flex items-center justify-center">
              <img src={`${import.meta.env.BASE_URL}LOGO_PROLUC.png`} alt="PROLUC Logo" className="h-full w-auto object-contain drop-shadow-lg" />
            </div>
            <p className="text-blue-50 text-sm font-medium opacity-95 max-w-xs leading-relaxed">
              Gestão curricular integrada para um futuro educacional moderno.
            </p>
          </div>
        </div>

        {/* Form Section */}
        <div className="w-full lg:w-1/2 flex flex-col items-center justify-start relative z-20 px-4 lg:px-12 -mt-16 lg:mt-0 pb-8 lg:pb-0 lg:bg-white lg:shadow-none lg:h-screen lg:overflow-y-auto">
          <div className="w-full max-w-md flex flex-col pt-4 lg:py-12 lg:my-auto">

            <div className="bg-white rounded-3xl shadow-xl border border-slate-100 overflow-visible flex flex-col lg:bg-transparent lg:rounded-none lg:shadow-none lg:border-none relative">

              <div className="pt-8 pb-4 px-8 text-center lg:p-0 lg:mb-8 lg:text-left">
                <h2 className="text-2xl lg:text-3xl font-bold text-slate-800 lg:text-slate-900 tracking-tight">{custom.titulo ?? 'Criar Conta'}</h2>
                <p className="text-slate-500 text-sm lg:text-base mt-2">
                  {custom.subtitulo ?? 'Preencha os dados abaixo para se cadastrar na plataforma.'}
                </p>
              </div>

              <div className="p-8 pt-2 space-y-6 lg:p-0 lg:space-y-6">
                <form className="space-y-5" onSubmit={handleSubmit}>
                  
                  {/* Tipo de Usuário */}
                  <div className="space-y-3">
                    <label className="block text-sm font-semibold text-slate-700 ml-1">{custom.label_tipo_usuario ?? 'Eu sou um(a)'}</label>
                    {!selectedClienteId ? (
                      <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-500">
                        Selecione primeiro o município para carregar os tipos de usuário disponíveis.
                      </div>
                    ) : null}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      {tiposCadastroDoCliente.map((option) => (
                        <label
                          key={option.id}
                          className={`
                            relative flex flex-col cursor-pointer rounded-xl border p-3 focus:outline-none transition-all duration-200
                            ${selectedTipoCadastroId === option.id
                              ? 'border-primary bg-primary/5 shadow-sm ring-1 ring-primary' 
                              : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                            }
                            ${!selectedClienteId ? 'pointer-events-none opacity-50' : ''}
                          `}
                        >
                          <div className="flex items-center justify-between w-full h-full text-center group">
                            <span className="text-sm font-medium text-slate-900 mx-auto leading-tight">{option.nome}</span>
                            <input
                              type="radio"
                              name="tipo_cadastro"
                              value={option.id}
                              className="sr-only"
                              checked={selectedTipoCadastroId === option.id}
                              onChange={() => setSelectedTipoCadastroId(option.id)}
                              disabled={!selectedClienteId}
                            />
                            {selectedTipoCadastroId === option.id && (
                              <span className="material-symbols-outlined absolute top-2 right-2 text-primary text-[18px]">
                                check_circle
                              </span>
                            )}
                          </div>
                        </label>
                      ))}
                    </div>
                    {selectedClienteId && tiposCadastroDoCliente.length === 0 ? (
                      <div className="rounded-xl border border-dashed border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                        Nenhum tipo de usuário está disponível para este município no momento.
                      </div>
                    ) : null}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Cliente / Município */}
                    <div className="space-y-2 relative">
                      <label className="block text-sm font-semibold text-slate-700 ml-1">{custom.label_municipio ?? 'Município (Cliente)'}</label>
                      <div className="relative group">
                        <input
                          type="text"
                          className="w-full h-12 pl-10 pr-10 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary text-slate-900 placeholder-slate-400 transition-all duration-200 outline-none font-medium shadow-sm hover:border-slate-300"
                          placeholder={custom.placeholder_municipio ?? 'Digite para buscar um município'}
                          value={clienteBusca}
                          onChange={(e) => {
                            setClienteBusca(e.target.value);
                            setIsClienteDropdownOpen(true);
                            if (selectedClienteId) {
                               setSelectedClienteId(''); // clear selection se digitar
                               setSelectedTipoCadastroId('');
                               setSelectedEscolaId(''); // clear escola together
                               setEscolaBusca('');
                            }
                          }}
                          onFocus={() => setIsClienteDropdownOpen(true)}
                          onBlur={() => {
                             setTimeout(() => setIsClienteDropdownOpen(false), 200);
                          }}
                          required={!selectedClienteId}
                        />
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors flex items-center">
                          <span className="material-symbols-outlined text-[18px]">location_city</span>
                        </div>
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 flex items-center pointer-events-none">
                          <span className="material-symbols-outlined text-[18px] transition-transform duration-200" style={{ transform: isClienteDropdownOpen ? 'rotate(180deg)' : 'none' }}>expand_more</span>
                        </div>
                      </div>

                      {/* Dropdown Options */}
                      {isClienteDropdownOpen && (
                        <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                           {filteredClientes.length === 0 ? (
                             <div className="p-3 text-sm text-slate-500 text-center">Nenhum município encontrado</div>
                           ) : (
                              filteredClientes.map(c => (
                                 <button
                                   key={c.id}
                                   type="button"
                                   className={`block w-full p-3 text-left text-sm hover:bg-slate-50 transition-colors ${selectedClienteId === c.id ? 'bg-primary/5 text-primary font-medium' : 'text-slate-700'}`}
                                   onMouseDown={(event) => {
                                      event.preventDefault();
                                      setSelectedClienteId(c.id);
                                      setClienteBusca(c.nome);
                                      setIsClienteDropdownOpen(false);
                                      setSelectedTipoCadastroId('');
                                      setSelectedEscolaId('');
                                      setEscolaBusca('');
                                      setCustom(c.cadastro_custom ?? {});
                                   }}
                                 >
                                    {c.nome}
                                 </button>
                               ))
                           )}
                        </div>
                      )}
                    </div>

                    {/* Escola */}
                    <div className="space-y-2 relative">
                      <label className="block text-sm font-semibold text-slate-700 ml-1">{custom.label_escola ?? 'Escola'}</label>
                      <div className="relative group">
                        <input
                          type="text"
                          className="w-full h-12 pl-10 pr-10 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary text-slate-900 placeholder-slate-400 transition-all duration-200 outline-none font-medium shadow-sm hover:border-slate-300 disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed"
                          placeholder={custom.placeholder_escola ?? 'Digite para buscar uma escola'}
                          value={escolaBusca}
                          onChange={(e) => {
                            setEscolaBusca(e.target.value);
                            setIsEscolaDropdownOpen(true);
                            if (selectedEscolaId) {
                               setSelectedEscolaId(''); // clear selection se digitar
                            }
                          }}
                          onFocus={() => setIsEscolaDropdownOpen(true)}
                          onBlur={() => {
                             // Timeout para permitir o click na opção registrar
                             setTimeout(() => setIsEscolaDropdownOpen(false), 200);
                          }}
                          disabled={!selectedClienteId}
                          required={!selectedEscolaId}
                        />
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors flex items-center">
                          <span className="material-symbols-outlined text-[18px]">school</span>
                        </div>
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 flex items-center pointer-events-none">
                          <span className="material-symbols-outlined text-[18px] transition-transform duration-200" style={{ transform: isEscolaDropdownOpen ? 'rotate(180deg)' : 'none' }}>expand_more</span>
                        </div>
                      </div>

                      {/* Dropdown Options */}
                      {isEscolaDropdownOpen && selectedClienteId !== '' && (
                        <div className="absolute z-50 w-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg max-h-60 overflow-y-auto">
                           {filteredEscolas.length === 0 ? (
                             <div className="p-3 text-sm text-slate-500 text-center">Nenhuma escola encontrada</div>
                           ) : (
                              filteredEscolas.map(e => (
                                 <button
                                   key={e.id}
                                   type="button"
                                   className={`block w-full p-3 text-left text-sm hover:bg-slate-50 transition-colors ${selectedEscolaId === e.id ? 'bg-primary/5 text-primary font-medium' : 'text-slate-700'}`}
                                   onMouseDown={(event) => {
                                      event.preventDefault();
                                      setSelectedEscolaId(e.id);
                                      setEscolaBusca(e.nome);
                                      setIsEscolaDropdownOpen(false);
                                   }}
                                 >
                                    {e.nome}
                                 </button>
                               ))
                           )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Nome */}
                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-slate-700 ml-1">{custom.label_nome ?? 'Nome Completo'}</label>
                    <div className="relative group">
                      <input
                        className="w-full h-12 pl-12 pr-4 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary text-slate-900 placeholder-slate-400 transition-all duration-200 outline-none font-medium shadow-sm hover:border-slate-300"
                        placeholder={custom.placeholder_nome ?? 'Seu nome'}
                        type="text"
                        value={nome}
                        onChange={(e) => setNome(e.target.value)}
                        required
                      />
                      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors">
                        <span className="material-symbols-outlined text-[20px]">person</span>
                      </div>
                    </div>
                  </div>

                  {/* Email */}
                  <div className="space-y-2">
                    <label className="block text-sm font-semibold text-slate-700 ml-1">{custom.label_email ?? 'E-mail'}</label>
                    <div className="relative group">
                      <input
                        className="w-full h-12 pl-12 pr-4 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary text-slate-900 placeholder-slate-400 transition-all duration-200 outline-none font-medium shadow-sm hover:border-slate-300"
                        placeholder={custom.placeholder_email ?? 'nome@instituicao.com.br'}
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        autoComplete="email"
                      />
                      <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors">
                        <span className="material-symbols-outlined text-[20px]">mail</span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Password */}
                    <div className="space-y-2">
                      <label className="block text-sm font-semibold text-slate-700 ml-1">{custom.label_senha ?? 'Senha'}</label>
                      <div className="relative group">
                        <input
                          className="w-full h-12 pl-10 pr-10 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary text-slate-900 placeholder-slate-400 transition-all duration-200 outline-none font-medium shadow-sm hover:border-slate-300"
                          placeholder="••••••••"
                          type={showPassword ? "text" : "password"}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          required
                        />
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors flex items-center">
                          <span className="material-symbols-outlined text-[18px]">lock</span>
                        </div>
                        <button
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer flex items-center"
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                        >
                          <span className="material-symbols-outlined text-[18px]">{showPassword ? 'visibility' : 'visibility_off'}</span>
                        </button>
                      </div>
                    </div>

                    {/* Confirm Password */}
                    <div className="space-y-2">
                      <label className="block text-sm font-semibold text-slate-700 ml-1">{custom.label_confirmar_senha ?? 'Confirmar Senha'}</label>
                      <div className="relative group">
                        <input
                          className="w-full h-12 pl-10 pr-10 bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary/50 focus:border-primary text-slate-900 placeholder-slate-400 transition-all duration-200 outline-none font-medium shadow-sm hover:border-slate-300"
                          placeholder="••••••••"
                          type={showConfirmPassword ? "text" : "password"}
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          required
                        />
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary transition-colors flex items-center">
                          <span className="material-symbols-outlined text-[18px]">lock</span>
                        </div>
                        <button
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors cursor-pointer flex items-center"
                          type="button"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                        >
                          <span className="material-symbols-outlined text-[18px]">{showConfirmPassword ? 'visibility' : 'visibility_off'}</span>
                        </button>
                      </div>
                    </div>
                  </div>

                  {(localError) && (
                    <div className="p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100 flex items-center gap-2">
                      <span className="material-symbols-outlined text-[18px]">error</span>
                      {localError}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={isSubmitting || status === 'loading'}
                    className="w-full h-14 bg-primary hover:bg-blue-700 lg:bg-primary lg:hover:bg-blue-700 group-hover:bg-blue-700 text-white font-bold text-lg rounded-xl shadow-lg shadow-blue-500/20 transform transition-all active:scale-[0.98] flex items-center justify-center gap-2 group mt-6 bg-gradient-to-r from-primary to-blue-600 lg:bg-none"
                  >
                    {isSubmitting ? 'Cadastrando...' : 'Cadastrar'}
                    <span className="material-symbols-outlined text-white group-hover:translate-x-1 transition-transform">how_to_reg</span>
                  </button>

                  <div className="text-center mt-6">
                    <p className="text-sm text-slate-500">
                      Já tem uma conta?{' '}
                      <Link to="/login" className="font-semibold text-primary hover:text-blue-700 transition-colors">
                        Fazer login
                      </Link>
                    </p>
                  </div>
                </form>
              </div>

            </div>

            {/* Footer Links */}
            <div className="mt-8 flex gap-6 text-sm font-medium text-slate-500 justify-center lg:mt-auto lg:pt-8 lg:gap-8 lg:text-slate-400 pb-8">
              <a className="hover:text-slate-700 lg:hover:text-slate-600 transition-colors" href="#">Ajuda</a>
              <a className="hover:text-slate-700 lg:hover:text-slate-600 transition-colors" href="#">Privacidade</a>
              <a className="hover:text-slate-700 lg:hover:text-slate-600 transition-colors" href="#">Termos</a>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
