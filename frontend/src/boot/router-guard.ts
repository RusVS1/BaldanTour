import { boot } from 'quasar/wrappers';
import { setupRouterGuards } from 'src/router/routes';

export default boot(({ router }) => {
  setupRouterGuards(router);
});
