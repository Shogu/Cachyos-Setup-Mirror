// Generated with AI for personal use. Do NOT upload to extensions.gnome.org (EGO) unless you understand JavaScript and can maintain this code.
// Assistant lancé par Topbar Center Widget dans un processus à part, pour que les
// bibliothèques d'agenda de GNOME (Evolution Data Server) ne soient jamais
// chargées dans GNOME Shell.
//   gjs -m edsCalendar.js list            → agendas modifiables, en JSON
//   gjs -m edsCalendar.js create <uid> <ics> → crée l'événement décrit en ICS, puis écrit OK
// La réponse sur la sortie standard fait foi : selon les versions, gjs peut
// planter en libérant les objets d'Evolution Data Server après le travail.
import System from 'system';

// Importés à l'exécution pour qu'une bibliothèque absente donne un message
// lisible au lieu d'une erreur fatale de gjs.
let ECal, EDataServer, ICalGLib;

const CONNECT_TIMEOUT_S = 20;
const READ_ONLY_BACKENDS = new Set(['contacts', 'weather']);

function calendars(registry) {
    return registry.list_enabled(EDataServer.SOURCE_EXTENSION_CALENDAR)
        .filter(source => !READ_ONLY_BACKENDS.has(source.get_extension(EDataServer.SOURCE_EXTENSION_CALENDAR)
            .get_backend_name()))
        .map(source => ({
            uid: source.get_uid(),
            name: source.get_display_name(),
            color: source.get_extension(EDataServer.SOURCE_EXTENSION_CALENDAR).get_color(),
        }));
}

function create(registry, uid, ics) {
    const source = registry.ref_source(uid);
    if (!source)
        throw new Error(`agenda introuvable : ${uid}`);
    const client = ECal.Client.connect_sync(source, ECal.ClientSourceType.EVENTS, CONNECT_TIMEOUT_S, null);
    if (client.is_readonly())
        throw new Error(`agenda en lecture seule : ${source.get_display_name()}`);
    const event = ICalGLib.Component.new_from_string(ics)
        .get_first_component(ICalGLib.ComponentKind.VEVENT_COMPONENT);
    client.create_object_sync(event, ECal.OperationFlags.NONE, null);
    print('OK');
}

const [mode, uid, ics] = ARGV;
try {
    try {
        ({default: ECal} = await import('gi://ECal?version=2.0'));
        ({default: EDataServer} = await import('gi://EDataServer?version=1.2'));
        // Sans version : on prend celle qu'ECal a déjà chargée (3.0 ou 4.0 selon libical).
        ({default: ICalGLib} = await import('gi://ICalGLib'));
    } catch (error) {
        throw new Error(`bibliothèques d’Evolution Data Server introuvables (${error.message})`);
    }
    const registry = EDataServer.SourceRegistry.new_sync(null);
    if (mode === 'list')
        print(JSON.stringify(calendars(registry)));
    else if (mode === 'create')
        create(registry, uid, ics);
    else
        throw new Error('usage : list | create <uid> <ics>');
} catch (error) {
    printerr(error.message);
    System.exit(1);
}
